from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from backend.v2.adapters.persistence import Database, FactRepository, IdentityRepository, RawStore
from backend.v2.domain import Document, Fact, Issuer


EXAMPLE = Path("docs/rework/contracts/fact.example.json")


@pytest.fixture
def stores(tmp_path):
    database = Database(tmp_path / "data" / "v2.sqlite3")
    database.migrate()
    identities = IdentityRepository(database)
    identities.put_issuer(
        Issuer.model_validate(
            {"issuerId": "synthetic-issuer", "legalName": "Synthetic Issuer", "domicileCountry": "US", "identifiers": []}
        )
    )
    return database, FactRepository(database), RawStore(tmp_path / "data")


def add_document(repository: FactRepository, raw_store: RawStore) -> Document:
    content = b"synthetic filing fixture\n"
    blob = raw_store.put(content)
    return repository.add_document(
        Document.model_validate(
            {
                "documentId": "synthetic-filing-2025",
                "provider": "synthetic_fixture",
                "sha256": blob.sha256,
                "relativePath": blob.relative_path,
                "sourceUrl": "https://example.org/synthetic-fixtures/annual-2025",
                "mediaType": "text/plain",
                "fetchedAt": "2026-09-13T10:00:00Z",
                "sizeBytes": blob.size_bytes,
            }
        )
    )


def fact_payload() -> dict:
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def fact_for_document(document: Document) -> Fact:
    payload = fact_payload()
    payload["evidence"][0]["sha256"] = document.sha256
    return Fact.model_validate(payload)


def test_document_and_fact_import_are_idempotent_and_recoverable(stores) -> None:
    _, repository, raw_store = stores
    document = add_document(repository, raw_store)
    assert repository.add_document(document).document_id == document.document_id

    fact = fact_for_document(document)
    repository.add_fact(fact)
    repository.add_fact(fact)
    assert repository.fact_count() == 1
    recovered = repository.get_fact(fact.fact_id)
    assert recovered is not None and recovered.value == "1000000"
    assert raw_store.read(document.sha256) == b"synthetic filing fixture\n"


def test_original_documents_and_observations_are_database_immutable(stores) -> None:
    database, repository, raw_store = stores
    document = add_document(repository, raw_store)
    repository.add_fact(fact_for_document(document))
    with pytest.raises(sqlite3.IntegrityError, match="immutable"):
        with database.transaction() as connection:
            connection.execute("UPDATE documents SET media_type = 'x' WHERE document_id = 'synthetic-filing-2025'")
    with pytest.raises(sqlite3.IntegrityError, match="immutable"):
        with database.transaction() as connection:
            connection.execute("UPDATE observations SET value_decimal = '0' WHERE fact_id = 'synthetic-revenue-fy2025'")


def test_missing_debt_round_trips_as_null_not_zero(stores) -> None:
    _, repository, raw_store = stores
    document = add_document(repository, raw_store)
    payload = fact_payload()
    payload["evidence"][0]["sha256"] = document.sha256
    payload.update(
        factId="synthetic-debt-missing",
        concept="debt.total",
        value=None,
        originalValue=None,
        originalUnit=None,
        originalScale=None,
        availability="missing",
        missingReason="not_reported",
    )
    fact = Fact.model_validate(payload)
    repository.add_fact(fact)
    recovered = repository.get_fact(fact.fact_id)
    assert recovered.value is None
    assert recovered.availability == "missing"


def test_explicit_clp_scale_a04_is_preserved(stores) -> None:
    _, repository, raw_store = stores
    document = add_document(repository, raw_store)
    payload = fact_payload()
    payload["evidence"][0]["sha256"] = document.sha256
    payload.update(
        factId="a04-clp-thousands",
        value="1234000",
        currency="CLP",
        originalValue="1234",
        originalUnit="CLP_thousands",
        originalScale=1000,
    )
    fact = Fact.model_validate(payload)
    repository.add_fact(fact)
    recovered = repository.get_fact(fact.fact_id)
    assert recovered.value == "1234000"
    assert recovered.original_value == "1234"
    assert recovered.original_scale == 1000


def test_raw_store_rejects_path_traversal(stores) -> None:
    _, _, raw_store = stores
    with pytest.raises(ValueError):
        raw_store.read("../secret")


def test_evidence_must_match_the_immutable_document(stores) -> None:
    _, repository, raw_store = stores
    add_document(repository, raw_store)
    with pytest.raises(ValueError, match="hash does not match"):
        repository.add_fact(Fact.model_validate(fact_payload()))
