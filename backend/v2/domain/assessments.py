"""Versioned assessment contracts shared by every future view."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import Field, field_validator, model_validator

from .common import CanonicalModel, CurrencyCode, Identifier, Sha256, utc_datetime


class AssessmentMode(str, Enum):
    FINANCIAL = "financial"
    PERSONAL = "personal"


class ResultState(str, Enum):
    AVAILABLE = "available"
    PENDING = "pending"
    BLOCKED = "blocked"
    NOT_APPLICABLE = "not_applicable"


class AssessmentResult(CanonicalModel):
    key: Identifier
    state: ResultState
    value: Any | None = None
    unit: str | None = None
    evidence_ids: list[Identifier] = Field(default_factory=list)
    reason: str | None = None

    @model_validator(mode="after")
    def state_matches_value(self) -> "AssessmentResult":
        if self.state == ResultState.AVAILABLE and self.value is None:
            raise ValueError("available result requires value")
        if self.state != ResultState.AVAILABLE and self.value is not None:
            raise ValueError("unavailable result cannot carry a value")
        if self.state != ResultState.AVAILABLE and not self.reason:
            raise ValueError("unavailable result requires reason")
        return self


class Coverage(CanonicalModel):
    possible_points: int = Field(default=100, gt=0)
    resolved_points: int = Field(ge=0)
    credited_points: int = Field(ge=0)
    pending_points: int = Field(ge=0)
    minimum_score: int = Field(ge=0)
    maximum_score: int = Field(ge=0)

    @model_validator(mode="after")
    def coherent_totals(self) -> "Coverage":
        if self.resolved_points + self.pending_points != self.possible_points:
            raise ValueError("resolvedPoints + pendingPoints must equal possiblePoints")
        if self.credited_points > self.resolved_points:
            raise ValueError("creditedPoints cannot exceed resolvedPoints")
        if self.minimum_score != self.credited_points:
            raise ValueError("minimumScore equals creditedPoints")
        if self.maximum_score != self.credited_points + self.pending_points:
            raise ValueError("maximumScore includes every unresolved point")
        return self


class Assessment(CanonicalModel):
    assessment_id: Identifier
    dataset_snapshot_id: Identifier
    instrument_id: Identifier
    listing_id: Identifier
    quote_currency: CurrencyCode
    mode: AssessmentMode
    scenario_set_revision: Identifier
    normalization_revision: Identifier
    thesis_revision: Identifier | None
    portfolio_snapshot_id: Identifier | None
    engine_versions: dict[str, Identifier]
    policy_versions: dict[str, Identifier]
    as_of: datetime
    results: list[AssessmentResult]
    coverage: Coverage
    blockers: list[str] = Field(default_factory=list)
    input_hash: Sha256

    @field_validator("as_of")
    @classmethod
    def as_of_is_aware(cls, value: datetime) -> datetime:
        return utc_datetime(value)

    @model_validator(mode="after")
    def personal_revisions(self) -> "Assessment":
        if self.mode == AssessmentMode.PERSONAL and self.thesis_revision is None:
            raise ValueError("personal assessment requires thesisRevision")
        if len({result.key for result in self.results}) != len(self.results):
            raise ValueError("assessment result keys must be unique")
        return self
