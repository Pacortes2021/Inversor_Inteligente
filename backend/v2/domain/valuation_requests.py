"""FCFF request contract only; valuation implementation is intentionally M4."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Literal

from pydantic import Field, field_validator, model_validator

from .common import (
    CanonicalModel,
    CurrencyCode,
    Identifier,
    NonnegativeDecimalString,
    decimal_value,
    next_anniversary,
    utc_datetime,
)
from .errors import ContractViolation, ErrorCode


class ClaimBridge(CanonicalModel):
    excess_cash: NonnegativeDecimalString
    non_operating_assets: NonnegativeDecimalString
    debt: NonnegativeDecimalString
    preferred: NonnegativeDecimalString
    minorities: NonnegativeDecimalString
    other_claims: NonnegativeDecimalString


class TerminalAssumptions(CanonicalModel):
    growth: float = Field(ge=0, le=0.1)
    roic: float = Field(gt=0, le=1)
    operating_margin: float = Field(gt=0, le=1)
    tax_rate: float = Field(ge=0, le=1)


class ForecastYear(CanonicalModel):
    revenue_growth: float = Field(gt=-1, le=1)
    operating_margin: float = Field(ge=-1, le=1)
    tax_rate: float = Field(ge=0, le=1)
    depreciation: NonnegativeDecimalString
    capex: NonnegativeDecimalString
    delta_operating_nwc: str = Field(pattern=r"^-?(0|[1-9][0-9]*)(\.[0-9]+)?$")
    forecast_start: date
    forecast_end: date
    cash_flow_at: date


NUMERIC_POINTERS = {
    "/baseRevenue",
    "/shares",
    "/claimBridge/excessCash",
    "/claimBridge/nonOperatingAssets",
    "/claimBridge/debt",
    "/claimBridge/preferred",
    "/claimBridge/minorities",
    "/claimBridge/otherClaims",
    "/wacc",
    "/terminal/growth",
    "/terminal/roic",
    "/terminal/operatingMargin",
    "/terminal/taxRate",
}
YEAR_POINTER_FIELDS = (
    "revenueGrowth",
    "operatingMargin",
    "taxRate",
    "depreciation",
    "capex",
    "deltaOperatingNwc",
)


class FcffSimulationRequest(CanonicalModel):
    request_id: Identifier
    dataset_snapshot_id: Identifier
    instrument_id: Identifier
    listing_id: Identifier
    scenario_set_revision: Identifier
    normalization_revision: Identifier
    model: Literal["fcff_driver_v1"]
    as_of: datetime
    valuation_date: date
    currency: CurrencyCode
    quote_currency: CurrencyCode
    base_revenue: NonnegativeDecimalString
    shares: NonnegativeDecimalString
    claim_bridge: ClaimBridge
    wacc: float = Field(gt=0, le=1)
    terminal: TerminalAssumptions
    years: list[ForecastYear] = Field(min_length=1, max_length=20)
    sbc_policy: Literal["expense_in_ebit"]
    forecast_convention: Literal["consecutive_12_month_periods"]
    tax_policy: Literal["no_loss_tax_credit"]
    shares_basis: Literal["valuation_common_equivalent"]
    evidence_ids: list[Identifier] = Field(min_length=1)
    input_bindings: dict[str, list[Identifier]]
    fx_fact_id: Identifier | None

    @field_validator("as_of")
    @classmethod
    def as_of_is_aware(cls, value: datetime) -> datetime:
        return utc_datetime(value)

    @model_validator(mode="after")
    def semantic_contract(self) -> "FcffSimulationRequest":
        if decimal_value(self.shares) <= Decimal("0"):
            raise ContractViolation(
                ErrorCode.NONPOSITIVE_SHARES, "shares must be positive", "/shares"
            )
        if decimal_value(self.base_revenue) <= Decimal("0"):
            raise ContractViolation(
                ErrorCode.NONPOSITIVE_BASE_REVENUE,
                "baseRevenue must be positive",
                "/baseRevenue",
            )
        if self.wacc <= self.terminal.growth:
            raise ContractViolation(
                ErrorCode.WACC_MUST_EXCEED_TERMINAL_GROWTH,
                "WACC must exceed terminal growth",
                "/wacc",
            )
        if self.terminal.growth / self.terminal.roic > 1:
            raise ContractViolation(
                ErrorCode.TERMINAL_REINVESTMENT_OUT_OF_DOMAIN,
                "terminal growth/ROIC cannot exceed 100%",
                "/terminal/roic",
            )
        if self.as_of.date() != self.valuation_date:
            raise ValueError("initial mode requires asOf UTC date to equal valuationDate")
        if self.currency != self.quote_currency and self.fx_fact_id is None:
            raise ContractViolation(
                ErrorCode.FX_REQUIRED,
                "different model and listing currencies require fxFactId",
                "/fxFactId",
            )
        if self.currency == self.quote_currency and self.fx_fact_id is not None:
            raise ValueError("same-currency request must not add an FX transformation")

        expected_start = self.valuation_date + timedelta(days=1)
        expected_end = next_anniversary(self.valuation_date)
        for index, year in enumerate(self.years):
            if year.forecast_start < expected_start:
                raise ContractViolation(
                    ErrorCode.OVERLAPPING_FORECAST_PERIODS,
                    "forecast periods overlap or include an already-valued day",
                    f"/years/{index}/forecastStart",
                )
            if year.forecast_start > expected_start:
                raise ContractViolation(
                    ErrorCode.NONCONSECUTIVE_FORECAST_PERIODS,
                    "forecast periods must be consecutive",
                    f"/years/{index}/forecastStart",
                )
            if year.forecast_end != expected_end:
                raise ContractViolation(
                    ErrorCode.NONCONSECUTIVE_FORECAST_PERIODS,
                    "each forecast is a consecutive twelve-month period",
                    f"/years/{index}/forecastEnd",
                )
            if year.cash_flow_at != year.forecast_end:
                raise ContractViolation(
                    ErrorCode.INVALID_CASH_FLOW_DATE,
                    "end-of-period convention requires cashFlowAt=forecastEnd",
                    f"/years/{index}/cashFlowAt",
                )
            expected_start = year.forecast_end + timedelta(days=1)
            expected_end = next_anniversary(year.forecast_end)

        required_pointers = set(NUMERIC_POINTERS)
        for index in range(len(self.years)):
            required_pointers.update(
                f"/years/{index}/{field}" for field in YEAR_POINTER_FIELDS
            )
        missing_pointers = sorted(required_pointers.difference(self.input_bindings))
        if missing_pointers:
            raise ContractViolation(
                ErrorCode.INPUT_BINDING_REQUIRED,
                f"numeric inputs require bindings: {', '.join(missing_pointers)}",
                "/inputBindings",
            )
        evidence = set(self.evidence_ids)
        if len(evidence) != len(self.evidence_ids):
            raise ValueError("evidenceIds must be unique")
        for pointer, references in self.input_bindings.items():
            if not references or not set(references).issubset(evidence):
                raise ContractViolation(
                    ErrorCode.UNKNOWN_REFERENCE,
                    f"binding {pointer} references evidence outside evidenceIds",
                    f"/inputBindings/{pointer}",
                )
        return self
