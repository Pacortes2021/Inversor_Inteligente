from __future__ import annotations

import hashlib
import json
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from backend.v2.adapters.persistence import Database, FactRepository, IdentityRepository
from backend.v2.adapters.providers.sec_mapping import POLICY_VERSION, SecFactMapper, policy_candidates
from backend.v2.domain import Document, Issuer, SecUnitFact


FIXTURES = Path("tests/v2/fixtures/sec")


def load_curated(name: str) -> tuple[dict, Document, list[SecUnitFact]]:
    path = FIXTURES / name
    raw = path.read_bytes()
    payload = json.loads(raw)
    digest = hashlib.sha256(raw).hexdigest()
    document = Document.model_validate(
        {
            "documentId": f"sec-curated-{payload['issuerId']}-2025",
            "provider": "sec",
            "sha256": digest,
            "relativePath": f"raw/{digest[:2]}/{digest}",
            "sourceUrl": payload["companyfactsUrl"],
            "mediaType": "application/json",
            "fetchedAt": payload["fetchedAt"],
            "sizeBytes": len(raw),
        }
    )
    facts = [
        SecUnitFact.model_validate(
            {
                "cik": payload["cik"],
                "taxonomy": "us-gaap",
                "label": item["tag"],
                "description": "Curated SEC reconciliation observation",
                "accessionNumber": payload["accessionNumber"],
                "documentId": document.document_id,
                **item,
            }
        )
        for item in payload["observations"]
    ]
    return payload, document, facts


@pytest.mark.parametrize("name", ["msft-2025-curated.json", "nflx-2025-curated.json"])
def test_curated_issuer_facts_reconcile_to_official_filing_tables(name: str) -> None:
    payload, document, source_facts = load_curated(name)
    mapper = SecFactMapper()

    mapped = [
        mapper.map(source, issuer_id=payload["issuerId"], document=document)
        for source in source_facts
    ]

    assert all(result.status == "mapped" for result in mapped)
    by_concept = {result.fact.concept: result.fact for result in mapped if result.fact}
    for concept, expected in payload["expected"].items():
        if concept != "debtTotal":
            assert by_concept[concept].value == expected
    debt = Decimal(by_concept["debt.current"].value) + Decimal(
        by_concept["debt.noncurrent"].value
    )
    assert format(debt, "f") == payload["expected"]["debtTotal"]
    assert by_concept["revenue"].period.label == "FY"
    assert by_concept["cash"].period.label == "instant"
    assert by_concept["capex"].value[0] != "-"
    assert by_concept["revenue"].context.tag == source_facts[0].tag
    assert payload["accessionNumber"] in by_concept["revenue"].evidence[0].locator


def test_mapped_facts_persist_with_exact_document_lineage(tmp_path) -> None:
    payload, document, source_facts = load_curated("msft-2025-curated.json")
    database = Database(tmp_path / "v2.sqlite3")
    database.migrate()
    identities = IdentityRepository(database)
    identities.put_issuer(
        Issuer(
            issuerId=payload["issuerId"],
            legalName="Microsoft Corporation",
            domicileCountry="US",
            identifiers=[],
        )
    )
    repository = FactRepository(database)
    repository.add_document(document)
    results = [
        SecFactMapper().map(source, issuer_id=payload["issuerId"], document=document)
        for source in source_facts
    ]

    for result in results:
        repository.add_fact(result.fact)

    assert repository.fact_count() == len(source_facts)
    recovered = repository.list_facts(issuer_id="msft", concept="revenue")[0]
    assert recovered.evidence[0].document_id == document.document_id
    assert recovered.context.taxonomy == "us-gaap"
    assert recovered.original_unit == "USD"


def test_policy_preserves_ordered_candidates_and_does_not_guess() -> None:
    payload, document, source_facts = load_curated("msft-2025-curated.json")
    source = source_facts[0]
    mapper = SecFactMapper()

    mapped = mapper.map(source, issuer_id=payload["issuerId"], document=document)
    extension = mapper.map(
        source.model_copy(update={"taxonomy": "msft"}),
        issuer_id=payload["issuerId"],
        document=document,
    )
    dimensional = mapper.map(
        source,
        issuer_id=payload["issuerId"],
        document=document,
        dimensions={"StatementBusinessSegmentsAxis": "CloudMember"},
    )
    wrong_unit = mapper.map(
        source.model_copy(update={"unit": "subscribers"}),
        issuer_id=payload["issuerId"],
        document=document,
    )

    assert mapped.policy_version == POLICY_VERSION
    assert mapped.candidate_tags == policy_candidates("revenue")
    assert extension.status == "unsupported"
    assert extension.reason == "unsupported_taxonomy_extension"
    assert dimensional.status == "blocked"
    assert dimensional.reason == "unsupported_dimensions"
    assert wrong_unit.status == "blocked"
    assert wrong_unit.reason == "unsupported_unit"


def test_money_mapping_preserves_non_usd_currency() -> None:
    payload, document, source_facts = load_curated("msft-2025-curated.json")
    source = source_facts[0].model_copy(update={"unit": "EUR"})

    result = SecFactMapper().map(source, issuer_id=payload["issuerId"], document=document)

    assert result.status == "mapped"
    assert result.fact.currency == "EUR"
    assert result.fact.original_unit == "EUR"


def test_share_basis_cannot_be_attached_without_an_instrument() -> None:
    payload, document, source_facts = load_curated("nflx-2025-curated.json")
    source = next(item for item in source_facts if item.unit == "USD/shares")

    result = SecFactMapper().map(
        source,
        issuer_id=payload["issuerId"],
        document=document,
        share_basis_id="nflx-split-2025",
    )

    assert result.status == "blocked"
    assert result.reason == "share_basis_requires_instrument"


def test_calendar_frame_is_not_mislabeled_as_a_noncalendar_fiscal_quarter() -> None:
    payload, document, source_facts = load_curated("msft-2025-curated.json")
    source = source_facts[0].model_copy(
        update={
            "start": date(2024, 7, 1),
            "end": date(2024, 9, 30),
            "form": "10-Q",
            "fiscal_year": 2025,
            "fiscal_period": "Q1",
            "frame": "CY2024Q3",
        }
    )

    result = SecFactMapper().map(source, issuer_id=payload["issuerId"], document=document)

    assert result.status == "blocked"
    assert result.reason == "fiscal_calendar_required"


def test_implausible_sec_duration_is_not_labeled_fy_or_fq() -> None:
    payload, document, source_facts = load_curated("msft-2025-curated.json")
    source = source_facts[0]
    two_year_fy = source.model_copy(
        update={"start": date(2023, 7, 1), "end": date(2025, 6, 30)}
    )
    one_day_quarter = source.model_copy(
        update={
            "start": date(2024, 1, 1),
            "end": date(2024, 1, 1),
            "form": "10-Q",
            "fiscal_year": 2024,
            "fiscal_period": "Q1",
            "frame": "CY2024Q1",
        }
    )

    long_result = SecFactMapper().map(
        two_year_fy, issuer_id=payload["issuerId"], document=document
    )
    short_result = SecFactMapper().map(
        one_day_quarter, issuer_id=payload["issuerId"], document=document
    )

    assert long_result.status == "blocked"
    assert long_result.reason == "unsupported_period_context"
    assert short_result.status == "blocked"
    assert short_result.reason == "invalid_period_duration"


def test_same_sec_observation_from_new_capture_has_new_immutable_identity(tmp_path) -> None:
    payload, document, source_facts = load_curated("msft-2025-curated.json")
    source = source_facts[0]
    later_document = document.model_copy(
        update={
            "document_id": f"{document.document_id}-updated",
            "sha256": "f" * 64,
            "relative_path": f"raw/ff/{'f' * 64}",
            "fetched_at": document.fetched_at + timedelta(days=1),
        }
    )
    later_source = source.model_copy(update={"document_id": later_document.document_id})
    mapper = SecFactMapper()
    original = mapper.map(source, issuer_id=payload["issuerId"], document=document).fact
    refreshed = mapper.map(
        later_source, issuer_id=payload["issuerId"], document=later_document
    ).fact

    assert original.fact_id != refreshed.fact_id
    assert original.evidence[0].document_id != refreshed.evidence[0].document_id

    database = Database(tmp_path / "v2.sqlite3")
    database.migrate()
    IdentityRepository(database).put_issuer(
        Issuer(
            issuerId=payload["issuerId"],
            legalName="Microsoft Corporation",
            domicileCountry="US",
            identifiers=[],
        )
    )
    repository = FactRepository(database)
    repository.add_document(document)
    repository.add_document(later_document)
    repository.add_fact(original)
    repository.add_fact(refreshed)
    assert repository.fact_count() == 2
