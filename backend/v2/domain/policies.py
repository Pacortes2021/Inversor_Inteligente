"""Versioned rules and durable decisions for canonical fact selection."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import Field, field_validator, model_validator

from .common import CanonicalModel, CurrencyCode, DecimalString, Identifier, Sha256, decimal_value, utc_datetime
from .facts import FactContext, FactPeriod, Unit


class SelectionMode(str, Enum):
    AS_REPORTED = "as_reported"
    LATEST_RESTATED = "latest_restated"


class SelectionStatus(str, Enum):
    SELECTED = "selected"
    CONFLICT = "conflict"
    MISSING = "missing"
    BLOCKED = "blocked"


class FactSelectionQuery(CanonicalModel):
    issuer_id: Identifier
    instrument_id: Identifier | None
    listing_id: Identifier | None
    concept: Identifier
    unit: Unit
    currency: CurrencyCode | None
    period: FactPeriod
    context: FactContext
    as_of: datetime
    mode: SelectionMode

    @field_validator("as_of")
    @classmethod
    def cutoff_is_aware(cls, value: datetime) -> datetime:
        return utc_datetime(value)


class SelectionPolicy(CanonicalModel):
    version: Identifier
    provider_priority: list[Identifier] = Field(default_factory=list)
    relative_tolerance: DecimalString = "0.001"
    absolute_tolerance: DecimalString = "0"
    date_only_session_cutoffs: dict[str, datetime] = Field(default_factory=dict)

    @field_validator("date_only_session_cutoffs")
    @classmethod
    def session_cutoffs_are_explicit_and_aware(
        cls, value: dict[str, datetime]
    ) -> dict[str, datetime]:
        normalized: dict[str, datetime] = {}
        for key, cutoff in value.items():
            try:
                identity, published_date = key.rsplit(":", 1)
                publication = date.fromisoformat(published_date)
            except (ValueError, TypeError) as error:
                raise ValueError("session cutoff keys must be '<identity>:YYYY-MM-DD'") from error
            if not identity:
                raise ValueError("session cutoff identity cannot be empty")
            normalized_cutoff = utc_datetime(cutoff)
            if normalized_cutoff.date() <= publication:
                raise ValueError("session cutoff must be after its publication date")
            normalized[key] = normalized_cutoff
        return normalized

    @model_validator(mode="after")
    def tolerances_are_nonnegative(self) -> "SelectionPolicy":
        if decimal_value(self.relative_tolerance) < 0 or decimal_value(self.absolute_tolerance) < 0:
            raise ValueError("selection tolerances must be nonnegative")
        if len(self.provider_priority) != len(set(self.provider_priority)):
            raise ValueError("provider priority cannot contain duplicates")
        return self


class CandidateDifference(CanonicalModel):
    left_fact_id: Identifier
    right_fact_id: Identifier
    absolute: DecimalString
    relative: DecimalString
    material: bool


class SelectionDecision(CanonicalModel):
    selection_decision_id: Identifier
    query: FactSelectionQuery
    policy_version: Identifier
    candidate_fact_ids: list[Identifier]
    selected_fact_id: Identifier | None
    status: SelectionStatus
    rule: Identifier
    differences: list[CandidateDifference] = Field(default_factory=list)
    content_hash: Sha256

    @model_validator(mode="after")
    def selected_shape(self) -> "SelectionDecision":
        if len(self.candidate_fact_ids) != len(set(self.candidate_fact_ids)):
            raise ValueError("candidate fact IDs must be unique")
        if self.status == SelectionStatus.SELECTED:
            if self.selected_fact_id is None or self.selected_fact_id not in self.candidate_fact_ids:
                raise ValueError("selected decision requires a selected candidate")
        elif self.selected_fact_id is not None:
            raise ValueError("unresolved decisions cannot select a fact")
        return self
