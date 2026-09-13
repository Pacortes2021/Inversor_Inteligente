"""Typed domain and API errors."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import Field

from .common import CanonicalModel, Identifier


class ErrorCode(str, Enum):
    MISSING_MUST_HAVE_NULL_VALUE = "missing_must_have_null_value"
    LISTING_REQUIRED = "listing_required"
    ORIGINAL_SCALE_DOES_NOT_RECONCILE = "original_scale_does_not_reconcile"
    INVALID_PERIOD = "invalid_period"
    INVALID_TIMESTAMP_ORDER = "invalid_timestamp_order"
    EVIDENCE_REQUIRED = "evidence_required"
    INVALID_LINEAGE = "invalid_lineage"
    NONPOSITIVE_SHARES = "nonpositive_shares"
    NONPOSITIVE_BASE_REVENUE = "nonpositive_base_revenue"
    WACC_MUST_EXCEED_TERMINAL_GROWTH = "wacc_must_exceed_terminal_growth"
    TERMINAL_REINVESTMENT_OUT_OF_DOMAIN = "terminal_reinvestment_out_of_domain"
    OVERLAPPING_FORECAST_PERIODS = "overlapping_forecast_periods"
    NONCONSECUTIVE_FORECAST_PERIODS = "nonconsecutive_forecast_periods"
    INVALID_CASH_FLOW_DATE = "invalid_cash_flow_date"
    FX_REQUIRED = "fx_required"
    INPUT_BINDING_REQUIRED = "input_binding_required"
    UNKNOWN_REFERENCE = "unknown_reference"
    PROBABILITIES_MUST_SUM_TO_ONE = "probabilities_must_sum_to_one"
    REVISION_CONFLICT = "revision_conflict"
    NOT_FOUND = "not_found"
    VALIDATION_ERROR = "validation_error"
    PROVIDER_UNAVAILABLE = "provider_unavailable"


class ContractViolation(ValueError):
    """Stable machine error produced by cross-field validation."""

    def __init__(self, code: ErrorCode | str, message: str, path: str = "") -> None:
        self.code = ErrorCode(code) if not isinstance(code, ErrorCode) else code
        self.path = path
        super().__init__(message)


class ErrorDetail(CanonicalModel):
    path: str = ""
    context: dict[str, Any] = Field(default_factory=dict)


class ApiError(CanonicalModel):
    code: ErrorCode
    message: str
    details: list[ErrorDetail] = Field(default_factory=list)
    request_id: Identifier
    retryable: bool = False
    retry_after_seconds: int | None = Field(default=None, ge=0)


class ErrorEnvelope(CanonicalModel):
    error: ApiError
