from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.v2.adapters.persistence import (
    Database,
    FactRepository,
    IdentityRepository,
    SelectionRepository,
)
from backend.v2.application.select_facts import select_fact
from backend.v2.domain import Fact, FactSelectionQuery, Issuer, SelectionPolicy


EXAMPLE = Path("docs/rework/contracts/fact.example.json")


def payload(
    fact_id: str,
    *,
    provider: str = "primary",
    value: str = "1000000",
    published_at: str | None = "2026-02-20T12:00:00Z",
    first_seen_at: str = "2026-02-20T12:05:00Z",
) -> dict:
    item = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    item.update(
        factId=fact_id,
        value=value,
        originalValue=value,
        originalUnit="USD",
        originalScale=1,
        publishedAt=published_at,
        firstSeenAt=first_seen_at,
        timestampPrecision=(
            "unknown" if published_at is None else "date" if len(published_at) == 10 else "second"
        ),
    )
    item["evidence"][0].update(
        provider=provider,
        documentId=None,
        sha256=None,
        url=f"https://example.org/{provider}/{fact_id}",
    )
    return item


def query_for(fact: Fact, *, as_of: str, mode: str = "as_reported") -> FactSelectionQuery:
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
            "asOf": as_of,
            "mode": mode,
        }
    )


POLICY = SelectionPolicy(
    version="selection-v1",
    providerPriority=["primary", "secondary"],
    relativeTolerance="0.001",
    absoluteTolerance="0",
)


def test_material_provider_conflict_blocks_selection() -> None:
    primary = Fact.model_validate(payload("primary-fact"))
    secondary = Fact.model_validate(payload("secondary-fact", provider="secondary", value="1200000"))

    decision = select_fact(
        [primary, secondary], query_for(primary, as_of="2026-03-01T00:00:00Z"), POLICY
    )

    assert decision.status == "conflict"
    assert decision.selected_fact_id is None
    assert decision.candidate_fact_ids == ["primary-fact", "secondary-fact"]
    assert decision.differences[0].material is True


def test_a23_later_revision_never_appears_before_publication() -> None:
    original = Fact.model_validate(payload("original", value="1000000"))
    revision = Fact.model_validate(
        payload(
            "restatement",
            value="1050000",
            published_at="2026-04-10T15:00:00Z",
            first_seen_at="2026-09-01T00:00:00Z",
        )
    )

    historical = select_fact(
        [original, revision], query_for(original, as_of="2026-04-10T14:59:59Z"), POLICY
    )
    current = select_fact(
        [original, revision],
        query_for(original, as_of="2026-09-13T00:00:00Z", mode="latest_restated"),
        POLICY,
    )

    assert historical.selected_fact_id == "original"
    assert historical.candidate_fact_ids == ["original"]
    assert current.selected_fact_id == "restatement"
    assert current.candidate_fact_ids == ["original", "restatement"]


def test_date_only_publication_requires_explicit_session_or_first_seen() -> None:
    dated = Fact.model_validate(
        payload("date-only", published_at="2026-02-20", first_seen_at="2026-02-22T00:00:00Z")
    )

    same_day = select_fact([dated], query_for(dated, as_of="2026-02-20T23:59:59Z"), POLICY)
    without_calendar = select_fact(
        [dated], query_for(dated, as_of="2026-02-21T20:00:00Z"), POLICY
    )
    policy_payload = POLICY.model_dump(mode="json", by_alias=True)
    policy_payload["dateOnlySessionCutoffs"] = {
        "synthetic-issuer:2026-02-20": "2026-02-23T21:00:00Z"
    }
    session_policy = SelectionPolicy.model_validate(policy_payload)
    at_explicit_session = select_fact(
        [dated],
        query_for(dated, as_of="2026-02-23T21:00:00Z"),
        session_policy,
    )
    first_seen = select_fact(
        [dated], query_for(dated, as_of="2026-02-22T00:00:00Z"), POLICY
    )

    assert same_day.status == "missing"
    assert without_calendar.status == "missing"
    assert at_explicit_session.selected_fact_id == "date-only"
    assert first_seen.selected_fact_id == "date-only"

    invalid_policy = POLICY.model_dump(mode="json", by_alias=True)
    invalid_policy["dateOnlySessionCutoffs"] = {
        "synthetic-issuer:2026-02-20": "2020-01-01T00:00:00Z"
    }
    with pytest.raises(ValueError, match="after its publication date"):
        SelectionPolicy.model_validate(invalid_policy)


def test_a24_other_listing_or_class_is_not_a_candidate() -> None:
    listing_a_payload = payload("price-a", value="10")
    listing_a_payload.update(
        instrumentId="class-a", listingId="listing-a", concept="price.close", unit="money_per_share"
    )
    listing_a = Fact.model_validate(listing_a_payload)
    listing_b_payload = payload("price-b", value="11")
    listing_b_payload.update(
        instrumentId="class-b", listingId="listing-b", concept="price.close", unit="money_per_share"
    )
    listing_b = Fact.model_validate(listing_b_payload)

    decision = select_fact(
        [listing_a, listing_b], query_for(listing_a, as_of="2026-03-01T00:00:00Z"), POLICY
    )

    assert decision.selected_fact_id == "price-a"
    assert decision.candidate_fact_ids == ["price-a"]


def test_invalid_or_declared_conflicting_facts_are_never_selected() -> None:
    invalid_payload = payload("invalid-fact")
    invalid_payload["quality"]["validation"] = "invalid"
    invalid = Fact.model_validate(invalid_payload)
    invalid_decision = select_fact(
        [invalid], query_for(invalid, as_of="2026-03-01T00:00:00Z"), POLICY
    )
    assert invalid_decision.status == "blocked"
    assert invalid_decision.selected_fact_id is None

    conflict_payload = payload("declared-conflict")
    conflict_payload["quality"]["reconciliation"] = "conflict"
    conflict = Fact.model_validate(conflict_payload)
    conflict_decision = select_fact(
        [conflict], query_for(conflict, as_of="2026-03-01T00:00:00Z"), POLICY
    )
    assert conflict_decision.status == "conflict"
    assert conflict_decision.selected_fact_id is None


def test_selection_decision_is_deterministic_idempotent_and_durable(tmp_path) -> None:
    database = Database(tmp_path / "v2.sqlite3")
    database.migrate()
    IdentityRepository(database).put_issuer(
        Issuer.model_validate(
            {
                "issuerId": "synthetic-issuer",
                "legalName": "Synthetic Issuer",
                "domicileCountry": "US",
                "identifiers": [],
            }
        )
    )
    fact = Fact.model_validate(payload("durable-fact"))
    FactRepository(database).add_fact(fact)
    decision = select_fact([fact], query_for(fact, as_of="2026-03-01T00:00:00Z"), POLICY)
    repeated = select_fact([fact], query_for(fact, as_of="2026-03-01T00:00:00Z"), POLICY)
    repository = SelectionRepository(database)

    assert repeated == decision
    assert repository.add(decision) == decision
    assert repository.add(decision) == decision
    assert repository.get(decision.selection_decision_id) == decision
