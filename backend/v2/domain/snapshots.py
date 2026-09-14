"""Immutable selected-data snapshot contracts."""

from __future__ import annotations

import hashlib
from datetime import datetime

from pydantic import Field, field_validator, model_validator

from .common import CanonicalModel, CurrencyCode, Identifier, Sha256, canonical_json, jsonable, utc_datetime
from .facts import Fact
from .policies import SelectionDecision


def dataset_snapshot_content_hash(
    *,
    instrument_id: str,
    listing_id: str,
    quote_currency: str,
    as_of: datetime,
    facts: list[Fact],
    decisions: list[SelectionDecision],
    price_fact_id: str,
    fx_fact_id: str | None,
    share_basis_id: str,
    selection_policy_version: str,
    period_policy_version: str,
) -> str:
    as_of = utc_datetime(as_of)
    by_id = {fact.fact_id: fact for fact in facts}
    fact_ids = sorted(by_id)
    seed = {
        "instrumentId": instrument_id,
        "listingId": listing_id,
        "quoteCurrency": quote_currency,
        "asOf": as_of.isoformat(),
        "factIds": fact_ids,
        "facts": [
            {
                "id": fact_id,
                "contentHash": hashlib.sha256(
                    canonical_json(jsonable(by_id[fact_id])).encode("utf-8")
                ).hexdigest(),
            }
            for fact_id in fact_ids
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
    return hashlib.sha256(canonical_json(seed).encode("utf-8")).hexdigest()


class DatasetSnapshot(CanonicalModel):
    dataset_snapshot_id: Identifier
    instrument_id: Identifier
    listing_id: Identifier
    quote_currency: CurrencyCode
    as_of: datetime
    fact_ids: list[Identifier] = Field(min_length=1)
    price_fact_id: Identifier
    fx_fact_id: Identifier | None
    share_basis_id: Identifier
    selection_policy_version: Identifier
    period_policy_version: Identifier
    content_hash: Sha256

    @field_validator("as_of")
    @classmethod
    def as_of_is_aware(cls, value: datetime) -> datetime:
        return utc_datetime(value)

    @model_validator(mode="after")
    def references_belong_to_snapshot(self) -> "DatasetSnapshot":
        if len(self.fact_ids) != len(set(self.fact_ids)):
            raise ValueError("snapshot fact IDs must be unique")
        required = {self.price_fact_id}
        if self.fx_fact_id is not None:
            required.add(self.fx_fact_id)
        if not required.issubset(set(self.fact_ids)):
            raise ValueError("priceFactId and fxFactId must belong to factIds")
        return self
