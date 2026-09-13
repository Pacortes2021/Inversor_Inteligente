"""Immutable selected-data snapshot contracts."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field, field_validator, model_validator

from .common import CanonicalModel, CurrencyCode, Identifier, Sha256, utc_datetime


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
