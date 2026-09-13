from __future__ import annotations

import json
import socket
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.v2.adapters.persistence import (
    Database,
    FactRepository,
    IdentityRepository,
    SelectionRepository,
    SnapshotRepository,
)
from backend.v2.application import build_snapshot, select_fact
from backend.v2.bootstrap import create_app
from backend.v2.domain import (
    Fact,
    FactSelectionQuery,
    Instrument,
    Issuer,
    Listing,
    SelectionPolicy,
    ShareBasis,
)


EXAMPLE = Path("docs/rework/contracts/fact.example.json")
AS_OF = datetime(2026, 9, 13, tzinfo=timezone.utc)
POLICY = SelectionPolicy(version="selection-v1", providerPriority=["primary"])


def fact_payload(fact_id: str, concept: str, value: str) -> dict:
    item = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    item.update(
        factId=fact_id,
        concept=concept,
        value=value,
        originalValue=value,
        originalUnit="USD",
        originalScale=1,
        instrumentId="instrument-a",
    )
    item["evidence"][0].update(
        provider="primary", documentId=None, sha256=None, url=f"https://example.org/{fact_id}"
    )
    if concept.startswith("price."):
        item.update(listingId="listing-a", unit="money_per_share")
        item["period"] = {
            "kind": "instant",
            "start": None,
            "end": "2026-09-12",
            "label": "instant",
            "fiscalYear": None,
            "fiscalQuarter": None,
        }
    return item


def selection_query(fact: Fact) -> FactSelectionQuery:
    return FactSelectionQuery.model_validate(
        {
            "issuerId": fact.issuer_id,
            "instrumentId": fact.instrument_id,
            "listingId": fact.listing_id,
            "concept": fact.concept,
            "unit": fact.unit,
            "currency": fact.currency,
            "period": fact.period.model_dump(mode="json", by_alias=True),
            "context": fact.context.model_dump(mode="json", by_alias=True),
            "asOf": AS_OF.isoformat(),
            "mode": "latest_restated",
        }
    )


def seed_snapshot(data_dir: Path):
    database = Database(data_dir / "v2.sqlite3")
    database.migrate()
    identities = IdentityRepository(database)
    identities.put_issuer(
        Issuer.model_validate(
            {
                "issuerId": "synthetic-issuer",
                "legalName": "Synthetic Issuer",
                "domicileCountry": "US",
                "identifiers": [],
            }
        )
    )
    identities.add_instrument(
        Instrument.model_validate(
            {
                "instrumentId": "instrument-a",
                "issuerId": "synthetic-issuer",
                "type": "common_stock",
                "shareClass": "A",
                "rightsSummary": None,
                "isin": None,
            }
        )
    )
    identities.add_listing(
        Listing.model_validate(
            {
                "listingId": "listing-a",
                "instrumentId": "instrument-a",
                "mic": "XNAS",
                "symbol": "SYN",
                "currency": "USD",
                "timezone": "America/New_York",
                "status": "active",
                "validFrom": "2020-01-01",
                "validTo": None,
            }
        )
    )
    identities.add_share_basis(
        ShareBasis.model_validate(
            {
                "shareBasisId": "basis-a",
                "instrumentId": "instrument-a",
                "asOf": "2026-09-12",
                "kind": "as_reported",
                "totalShares": "100",
                "components": [
                    {
                        "componentId": "common-a",
                        "kind": "common_outstanding",
                        "shares": "100",
                        "treatment": "included_in_denominator",
                        "evidenceId": "evidence-basis-a",
                    }
                ],
                "version": "basis-v1",
            }
        )
    )
    facts = [
        Fact.model_validate(fact_payload("price-a", "price.close", "10")),
        Fact.model_validate(fact_payload("revenue-a", "revenue", "1000000")),
    ]
    fact_repository = FactRepository(database)
    for fact in facts:
        fact_repository.add_fact(fact)
    decisions = [select_fact([fact], selection_query(fact), POLICY) for fact in facts]
    selection_repository = SelectionRepository(database)
    for decision in decisions:
        selection_repository.add(decision)
    snapshot = build_snapshot(
        instrument_id="instrument-a",
        listing_id="listing-a",
        quote_currency="USD",
        as_of=AS_OF,
        decisions=decisions,
        facts=facts,
        price_fact_id="price-a",
        fx_fact_id=None,
        share_basis_id="basis-a",
        selection_policy_version="selection-v1",
        period_policy_version="period-v1",
    )
    snapshot_repository = SnapshotRepository(database)
    decision_ids = sorted(decision.selection_decision_id for decision in decisions)
    snapshot_repository.add(snapshot, decision_ids)
    return database, snapshot, decisions, facts


def row_counts(database: Database) -> tuple[int, int, int]:
    with database.connect() as connection:
        return tuple(
            connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            for table in ("snapshots", "observations", "selection_decisions")
        )


def test_same_inputs_and_policies_produce_the_same_snapshot_hash(tmp_path) -> None:
    _, snapshot, decisions, facts = seed_snapshot(tmp_path / "data")
    repeated = build_snapshot(
        instrument_id="instrument-a",
        listing_id="listing-a",
        quote_currency="USD",
        as_of=AS_OF,
        decisions=decisions,
        facts=facts,
        price_fact_id="price-a",
        fx_fact_id=None,
        share_basis_id="basis-a",
        selection_policy_version="selection-v1",
        period_policy_version="period-v1",
    )
    assert repeated.dataset_snapshot_id == snapshot.dataset_snapshot_id
    assert repeated.content_hash == snapshot.content_hash


def test_a16_snapshot_replays_offline_and_get_does_not_write(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    database, snapshot, _, _ = seed_snapshot(data_dir)
    before = row_counts(database)
    monkeypatch.setattr(
        socket,
        "create_connection",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("network access")),
    )
    client = TestClient(create_app(data_dir))

    first = client.get(f"/api/v2/snapshots/{snapshot.dataset_snapshot_id}")
    second = client.get(f"/api/v2/snapshots/{snapshot.dataset_snapshot_id}")
    fact = client.get("/api/v2/facts/price-a")

    assert first.status_code == second.status_code == fact.status_code == 200
    assert first.json() == second.json()
    assert {item["factId"] for item in first.json()["facts"]} == {"price-a", "revenue-a"}
    assert row_counts(database) == before


def test_snapshot_rejects_price_from_another_listing(tmp_path) -> None:
    _, _, decisions, facts = seed_snapshot(tmp_path / "data")
    with pytest.raises(ValueError, match="price fact does not match"):
        build_snapshot(
            instrument_id="instrument-a",
            listing_id="listing-b",
            quote_currency="USD",
            as_of=AS_OF,
            decisions=decisions,
            facts=facts,
            price_fact_id="price-a",
            fx_fact_id=None,
            share_basis_id="basis-a",
            selection_policy_version="selection-v1",
            period_policy_version="period-v1",
        )
