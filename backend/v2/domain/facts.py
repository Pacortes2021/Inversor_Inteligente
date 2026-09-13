"""Canonical financial fact and lineage contracts."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Annotated, Literal

from pydantic import Field, HttpUrl, field_validator, model_validator

from .common import (
    CanonicalModel,
    CurrencyCode,
    DecimalString,
    Identifier,
    Sha256,
    decimal_value,
    utc_datetime,
)
from .errors import ContractViolation, ErrorCode


class Unit(str, Enum):
    MONEY = "money"
    MONEY_PER_SHARE = "money_per_share"
    SHARES = "shares"
    RATIO = "ratio"
    PERCENT = "percent"
    COUNT = "count"


class PeriodKind(str, Enum):
    INSTANT = "instant"
    DURATION = "duration"


class PeriodLabel(str, Enum):
    FY = "FY"
    FQ = "FQ"
    YTD = "YTD"
    TTM = "TTM"
    INSTANT = "instant"


class FactPeriod(CanonicalModel):
    kind: PeriodKind
    start: date | None
    end: date
    label: PeriodLabel
    fiscal_year: int | None
    fiscal_quarter: int | None = Field(default=None, ge=1, le=4)

    @model_validator(mode="after")
    def period_shape(self) -> "FactPeriod":
        if self.kind == PeriodKind.INSTANT:
            if self.start is not None or self.label != PeriodLabel.INSTANT:
                raise ContractViolation(
                    ErrorCode.INVALID_PERIOD,
                    "instant periods require start=null and label=instant",
                    "/period",
                )
        else:
            if self.start is None or self.start > self.end or self.label == PeriodLabel.INSTANT:
                raise ContractViolation(
                    ErrorCode.INVALID_PERIOD,
                    "duration periods require ordered start/end and a duration label",
                    "/period",
                )
        if self.label == PeriodLabel.FQ and self.fiscal_quarter is None:
            raise ContractViolation(
                ErrorCode.INVALID_PERIOD, "FQ requires fiscalQuarter", "/period/fiscalQuarter"
            )
        if self.label != PeriodLabel.FQ and self.fiscal_quarter is not None:
            raise ContractViolation(
                ErrorCode.INVALID_PERIOD,
                "fiscalQuarter is only valid for FQ",
                "/period/fiscalQuarter",
            )
        return self


class FactShareBasis(str, Enum):
    NOT_APPLICABLE = "not_applicable"
    AS_REPORTED = "as_reported"
    SPLIT_ADJUSTED = "split_adjusted"
    UNKNOWN = "unknown"


class FactContext(CanonicalModel):
    consolidated: bool | None
    dimensions: dict[str, str]
    taxonomy: str | None
    tag: str | None
    share_basis: FactShareBasis
    share_basis_id: Identifier | None = None

    @model_validator(mode="after")
    def linked_share_basis(self) -> "FactContext":
        if self.share_basis == FactShareBasis.SPLIT_ADJUSTED and self.share_basis_id is None:
            raise ValueError("split_adjusted requires shareBasisId")
        return self


class TimestampPrecision(str, Enum):
    SECOND = "second"
    DATE = "date"
    UNKNOWN = "unknown"


class FactOrigin(str, Enum):
    REPORTED = "reported"
    DERIVED = "derived"
    ESTIMATE = "estimate"
    ASSUMPTION = "assumption"
    MANUAL_JUDGMENT = "manual_judgment"


class Availability(str, Enum):
    AVAILABLE = "available"
    MISSING = "missing"
    NOT_APPLICABLE = "not_applicable"
    UNSUPPORTED = "unsupported"
    BLOCKED = "blocked"


class Freshness(str, Enum):
    CURRENT = "current"
    STALE = "stale"
    UNKNOWN = "unknown"


class Reconciliation(str, Enum):
    SINGLE_SOURCE = "single_source"
    MATCHED = "matched"
    CONFLICT = "conflict"
    NOT_CHECKED = "not_checked"


class ValidationState(str, Enum):
    VALID = "valid"
    INVALID = "invalid"
    PENDING = "pending"


class FactQuality(CanonicalModel):
    freshness: Freshness
    reconciliation: Reconciliation
    validation: ValidationState


class Evidence(CanonicalModel):
    provider: Identifier
    document_id: Identifier | None
    url: HttpUrl | None
    locator: str | None
    sha256: Sha256 | None

    @model_validator(mode="after")
    def is_verifiable(self) -> "Evidence":
        if not any((self.document_id, self.url, self.sha256)):
            raise ContractViolation(
                ErrorCode.EVIDENCE_REQUIRED,
                "evidence requires an identifiable document, URL or hash; locator alone is insufficient",
                "/evidence",
            )
        return self


class ScaleParameters(CanonicalModel):
    original_scale: int = Field(strict=True, ge=1)
    target_scale: Annotated[int, Field(strict=True, ge=1, le=1)]


class FxParameters(CanonicalModel):
    source_currency: CurrencyCode
    target_currency: CurrencyCode
    operation: Literal["multiply", "divide"]

    @model_validator(mode="after")
    def changes_currency(self) -> "FxParameters":
        if self.source_currency == self.target_currency:
            raise ValueError("FX transformation must change currency")
        return self


class SplitParameters(CanonicalModel):
    factor: DecimalString
    target_date: date
    corporate_action_id: Identifier

    @model_validator(mode="after")
    def positive_factor(self) -> "SplitParameters":
        if decimal_value(self.factor) <= 0:
            raise ValueError("split factor must be positive")
        return self


class NormalizationParameters(CanonicalModel):
    method: Identifier
    rationale: str = Field(min_length=1)


class ScaleTransformation(CanonicalModel):
    kind: Literal["scale"]
    name: Identifier
    version: Identifier
    parameters: ScaleParameters
    fx_fact_id: None = None
    share_basis_id: None = None
    adjustment_ids: list[Identifier] = Field(default_factory=list)

    @model_validator(mode="after")
    def scale_has_no_unrelated_references(self) -> "ScaleTransformation":
        if self.adjustment_ids:
            raise ValueError("scale transformation cannot contain adjustmentIds")
        return self


class FxTransformation(CanonicalModel):
    kind: Literal["fx"]
    name: Identifier
    version: Identifier
    parameters: FxParameters
    fx_fact_id: Identifier
    share_basis_id: None = None
    adjustment_ids: list[Identifier] = Field(default_factory=list)

    @model_validator(mode="after")
    def fx_has_no_unrelated_references(self) -> "FxTransformation":
        if self.adjustment_ids:
            raise ValueError("FX transformation cannot contain adjustmentIds")
        return self


class SplitTransformation(CanonicalModel):
    kind: Literal["split"]
    name: Identifier
    version: Identifier
    parameters: SplitParameters
    fx_fact_id: None = None
    share_basis_id: Identifier
    adjustment_ids: list[Identifier] = Field(default_factory=list)

    @model_validator(mode="after")
    def split_has_no_unrelated_references(self) -> "SplitTransformation":
        if self.adjustment_ids:
            raise ValueError("split transformation cannot contain adjustmentIds")
        return self


class NormalizationTransformation(CanonicalModel):
    kind: Literal["normalization"]
    name: Identifier
    version: Identifier
    parameters: NormalizationParameters
    fx_fact_id: None = None
    share_basis_id: None = None
    adjustment_ids: list[Identifier] = Field(min_length=1)


Transformation = Annotated[
    ScaleTransformation | FxTransformation | SplitTransformation | NormalizationTransformation,
    Field(discriminator="kind"),
]


PRICE_CONCEPTS = {"price.close", "price.open", "price.high", "price.low"}


class Fact(CanonicalModel):
    fact_id: Identifier
    issuer_id: Identifier
    instrument_id: Identifier | None
    listing_id: Identifier | None
    concept: Identifier
    value: DecimalString | None
    unit: Unit
    currency: CurrencyCode | None
    scale: Annotated[int, Field(strict=True, ge=1, le=1)] = 1
    original_value: DecimalString | None
    original_unit: str | None
    original_scale: int | None = Field(default=None, ge=1)
    period: FactPeriod
    context: FactContext
    published_at: datetime | date | None
    first_seen_at: datetime
    retrieved_at: datetime
    timestamp_precision: TimestampPrecision
    origin: FactOrigin
    availability: Availability
    missing_reason: str | None
    quality: FactQuality
    evidence: list[Evidence]
    input_fact_ids: list[Identifier] = Field(default_factory=list)
    transformation: Transformation | None

    @field_validator("first_seen_at", "retrieved_at")
    @classmethod
    def timestamps_are_aware(cls, value: datetime) -> datetime:
        return utc_datetime(value)

    @field_validator("published_at", mode="before")
    @classmethod
    def preserve_publication_precision(cls, value: object) -> object:
        if isinstance(value, str) and len(value) == 10:
            try:
                return date.fromisoformat(value)
            except ValueError:
                return value
        return value

    @field_validator("published_at")
    @classmethod
    def publication_timestamp_is_aware(cls, value: datetime | date | None) -> datetime | date | None:
        if isinstance(value, datetime):
            return utc_datetime(value)
        return value

    @model_validator(mode="after")
    def semantic_contract(self) -> "Fact":
        available = self.availability == Availability.AVAILABLE
        if available != (self.value is not None):
            raise ContractViolation(
                ErrorCode.MISSING_MUST_HAVE_NULL_VALUE,
                "available facts require a value; all other states require null",
                "/value",
            )
        if available != (self.missing_reason is None):
            raise ContractViolation(
                ErrorCode.MISSING_MUST_HAVE_NULL_VALUE,
                "unavailable facts require a missingReason",
                "/missingReason",
            )
        monetary = self.unit in (Unit.MONEY, Unit.MONEY_PER_SHARE)
        if available and monetary and self.currency is None:
            raise ValueError("available monetary facts require currency")
        if not monetary and self.currency is not None:
            raise ValueError("non-monetary facts must not have currency")
        if self.first_seen_at > self.retrieved_at:
            raise ContractViolation(
                ErrorCode.INVALID_TIMESTAMP_ORDER,
                "firstSeenAt must not be after retrievedAt",
                "/firstSeenAt",
            )
        if self.published_at is None and self.timestamp_precision != TimestampPrecision.UNKNOWN:
            raise ContractViolation(
                ErrorCode.INVALID_TIMESTAMP_ORDER,
                "unknown publication requires timestampPrecision=unknown",
                "/timestampPrecision",
            )
        if isinstance(self.published_at, datetime) and self.timestamp_precision != TimestampPrecision.SECOND:
            raise ContractViolation(
                ErrorCode.INVALID_TIMESTAMP_ORDER,
                "datetime publication requires timestampPrecision=second",
                "/timestampPrecision",
            )
        if self.published_at is not None and not isinstance(self.published_at, datetime) and self.timestamp_precision != TimestampPrecision.DATE:
            raise ContractViolation(
                ErrorCode.INVALID_TIMESTAMP_ORDER,
                "date-only publication requires timestampPrecision=date",
                "/timestampPrecision",
            )
        if isinstance(self.published_at, datetime):
            publication_after_retrieval = self.published_at > self.retrieved_at
        else:
            publication_after_retrieval = (
                self.published_at is not None and self.published_at > self.retrieved_at.date()
            )
        if publication_after_retrieval:
            raise ContractViolation(
                ErrorCode.INVALID_TIMESTAMP_ORDER,
                "publishedAt must not be after retrievedAt",
                "/publishedAt",
            )
        if self.origin == FactOrigin.REPORTED and available and self.period.end > self.retrieved_at.date():
            raise ContractViolation(
                ErrorCode.INVALID_PERIOD,
                "reported facts cannot describe a future completed period",
                "/period/end",
            )
        if self.concept in PRICE_CONCEPTS and available:
            if self.instrument_id is None or self.listing_id is None or self.unit != Unit.MONEY_PER_SHARE:
                raise ContractViolation(
                    ErrorCode.LISTING_REQUIRED,
                    "available prices require instrument, listing and money_per_share",
                    "/listingId",
                )
        if self.origin == FactOrigin.REPORTED and available and not self.evidence:
            raise ContractViolation(
                ErrorCode.EVIDENCE_REQUIRED,
                "reported available facts require evidence",
                "/evidence",
            )
        if self.origin == FactOrigin.DERIVED and available:
            if not self.input_fact_ids or self.transformation is None:
                raise ContractViolation(
                    ErrorCode.INVALID_LINEAGE,
                    "derived facts require inputs and a typed transformation",
                    "/inputFactIds",
                )
        dependencies = self.fact_dependency_ids()
        if self.fact_id in dependencies or len(dependencies) != len(set(dependencies)):
            raise ContractViolation(
                ErrorCode.INVALID_LINEAGE,
                "lineage cannot be self-referential or duplicated",
                "/inputFactIds",
            )
        if isinstance(self.transformation, FxTransformation) and self.transformation.fx_fact_id not in self.input_fact_ids:
            raise ContractViolation(
                ErrorCode.INVALID_LINEAGE,
                "FX fact must also be declared as an inputFactId",
                "/transformation/fxFactId",
            )
        if available and self.original_value is not None and self.original_scale is not None:
            simple_scale = self.transformation is None or isinstance(self.transformation, ScaleTransformation)
            if isinstance(self.transformation, ScaleTransformation) and self.transformation.parameters.original_scale != self.original_scale:
                raise ContractViolation(
                    ErrorCode.ORIGINAL_SCALE_DOES_NOT_RECONCILE,
                    "scale parameters must match originalScale",
                    "/transformation/parameters/originalScale",
                )
            if simple_scale and decimal_value(self.value) != decimal_value(self.original_value) * self.original_scale:
                raise ContractViolation(
                    ErrorCode.ORIGINAL_SCALE_DOES_NOT_RECONCILE,
                    "canonical value must equal originalValue × originalScale for scale-only conversion",
                    "/value",
                )
        return self

    def fact_dependency_ids(self) -> list[str]:
        dependencies = list(self.input_fact_ids)
        if isinstance(self.transformation, FxTransformation):
            # Keep the edge explicit even though semantic validation also
            # requires it in inputFactIds; de-duplicate for graph traversal.
            if self.transformation.fx_fact_id not in dependencies:
                dependencies.append(self.transformation.fx_fact_id)
        return dependencies


def validate_lineage(facts: list[Fact]) -> None:
    """Validate that all references exist and that the lineage graph is acyclic."""

    by_id = {fact.fact_id: fact for fact in facts}
    if len(by_id) != len(facts):
        raise ContractViolation(ErrorCode.INVALID_LINEAGE, "fact IDs must be unique")
    for fact in facts:
        for input_id in fact.fact_dependency_ids():
            if input_id not in by_id:
                raise ContractViolation(
                    ErrorCode.UNKNOWN_REFERENCE,
                    f"unknown input fact {input_id}",
                    f"/{fact.fact_id}/inputFactIds",
                )

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(fact_id: str) -> None:
        if fact_id in visiting:
            raise ContractViolation(ErrorCode.INVALID_LINEAGE, "fact lineage contains a cycle")
        if fact_id in visited:
            return
        visiting.add(fact_id)
        for input_id in by_id[fact_id].fact_dependency_ids():
            visit(input_id)
        visiting.remove(fact_id)
        visited.add(fact_id)

    for identifier in by_id:
        visit(identifier)
