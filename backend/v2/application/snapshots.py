"""Pure construction of immutable, content-addressed dataset snapshots."""

from __future__ import annotations

import hashlib
from datetime import datetime

from ..domain.common import canonical_json, jsonable, utc_datetime
from ..domain.facts import Fact, Unit
from ..domain.policies import SelectionDecision, SelectionStatus
from ..domain.snapshots import DatasetSnapshot


def build_snapshot(
    *,
    instrument_id: str,
    listing_id: str,
    quote_currency: str,
    as_of: datetime,
    decisions: list[SelectionDecision],
    facts: list[Fact],
    price_fact_id: str,
    fx_fact_id: str | None,
    share_basis_id: str,
    selection_policy_version: str,
    period_policy_version: str,
) -> DatasetSnapshot:
    as_of = utc_datetime(as_of)
    if not decisions or any(decision.status != SelectionStatus.SELECTED for decision in decisions):
        raise ValueError("a snapshot requires resolved selection decisions")
    if any(decision.query.as_of != as_of for decision in decisions):
        raise ValueError("selection decisions must use the snapshot cutoff")
    if any(decision.policy_version != selection_policy_version for decision in decisions):
        raise ValueError("selection policy version does not match the decisions")

    selected_ids = sorted({decision.selected_fact_id for decision in decisions if decision.selected_fact_id})
    by_id = {fact.fact_id: fact for fact in facts}
    if set(selected_ids) != set(by_id):
        raise ValueError("facts must exactly match selected decision outputs")
    price = by_id.get(price_fact_id)
    if (
        price is None
        or price.instrument_id != instrument_id
        or price.listing_id != listing_id
        or price.unit != Unit.MONEY_PER_SHARE
        or price.currency != quote_currency
        or not price.concept.startswith("price.")
    ):
        raise ValueError("price fact does not match snapshot instrument, listing and currency")
    if any(
        fact.fact_id != fx_fact_id and fact.issuer_id != price.issuer_id for fact in facts
    ):
        raise ValueError("all snapshot facts must belong to the price issuer")
    if any(
        decision.selected_fact_id != fx_fact_id
        and (
            decision.query.issuer_id != price.issuer_id
            or (
                decision.query.instrument_id is not None
                and decision.query.instrument_id != instrument_id
            )
            or (
                decision.query.listing_id is not None
                and decision.query.listing_id != listing_id
            )
        )
        for decision in decisions
    ):
        raise ValueError("selection decision identity does not match snapshot identity")
    if fx_fact_id is not None:
        fx = by_id.get(fx_fact_id)
        if fx is None or not fx.concept.startswith("fx."):
            raise ValueError("FX fact must be a selected FX observation")

    seed = {
        "instrumentId": instrument_id,
        "listingId": listing_id,
        "quoteCurrency": quote_currency,
        "asOf": as_of.isoformat(),
        "factIds": selected_ids,
        "facts": [
            {
                "id": fact_id,
                "contentHash": hashlib.sha256(
                    canonical_json(jsonable(by_id[fact_id])).encode("utf-8")
                ).hexdigest(),
            }
            for fact_id in selected_ids
        ],
        "priceFactId": price_fact_id,
        "fxFactId": fx_fact_id,
        "shareBasisId": share_basis_id,
        "selectionPolicyVersion": selection_policy_version,
        "periodPolicyVersion": period_policy_version,
        "selectionDecisions": [
            {"id": item.selection_decision_id, "contentHash": item.content_hash}
            for item in sorted(decisions, key=lambda item: item.selection_decision_id)
        ],
    }
    content_hash = hashlib.sha256(canonical_json(seed).encode("utf-8")).hexdigest()
    return DatasetSnapshot(
        datasetSnapshotId=f"snapshot-{content_hash[:24]}",
        instrumentId=instrument_id,
        listingId=listing_id,
        quoteCurrency=quote_currency,
        asOf=as_of,
        factIds=selected_ids,
        priceFactId=price_fact_id,
        fxFactId=fx_fact_id,
        shareBasisId=share_basis_id,
        selectionPolicyVersion=selection_policy_version,
        periodPolicyVersion=period_policy_version,
        contentHash=content_hash,
    )
