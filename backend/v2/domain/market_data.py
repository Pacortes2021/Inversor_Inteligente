"""Typed secondary-market observations with explicit adjustment semantics."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Literal

from pydantic import Field, field_validator, model_validator

from .common import (
    CanonicalModel,
    CurrencyCode,
    DecimalString,
    Identifier,
    NonnegativeDecimalString,
    utc_datetime,
    decimal_value,
)
from .documents import Document


class PriceBasis(str, Enum):
    RAW = "raw"
    SPLIT_ADJUSTED = "split_adjusted"
    TOTAL_RETURN = "total_return"


class MarketPrice(CanonicalModel):
    issuer_id: Identifier
    instrument_id: Identifier
    listing_id: Identifier
    mic: str = Field(pattern=r"^[A-Z0-9]{4}$")
    provider_symbol: Identifier
    session_date: date
    value: DecimalString
    currency: CurrencyCode
    basis: PriceBasis
    source_field: Identifier
    split_adjustment_as_of: date | None = None
    document_id: Identifier

    @model_validator(mode="after")
    def adjustment_metadata_matches_basis(self) -> "MarketPrice":
        if decimal_value(self.value) <= 0:
            raise ValueError("market price must be positive")
        adjusted = self.basis == PriceBasis.SPLIT_ADJUSTED
        if adjusted != (self.split_adjustment_as_of is not None):
            raise ValueError("only split-adjusted prices require splitAdjustmentAsOf")
        return self


class MarketSession(CanonicalModel):
    listing_id: Identifier
    mic: str = Field(pattern=r"^[A-Z0-9]{4}$")
    provider_symbol: Identifier
    session_date: date
    timezone: Identifier
    opens_at: datetime | None
    closes_at: datetime | None
    source_exchange_code: str | None
    schedule_source: Literal["yahoo_current_metadata", "yahoo_observed_price_date"]
    document_id: Identifier

    @field_validator("opens_at", "closes_at")
    @classmethod
    def session_timestamps_are_aware(cls, value: datetime | None) -> datetime | None:
        return None if value is None else utc_datetime(value)

    @model_validator(mode="after")
    def session_times_are_paired(self) -> "MarketSession":
        if (self.opens_at is None) != (self.closes_at is None):
            raise ValueError("session open and close must both be known or both be absent")
        if self.opens_at is not None and self.opens_at >= self.closes_at:
            raise ValueError("market session open must precede close")
        return self


class MarketCalendarCoverage(CanonicalModel):
    listing_id: Identifier
    mic: str = Field(pattern=r"^[A-Z0-9]{4}$")
    provider_symbol: Identifier
    timezone: Identifier
    coverage_start: date
    coverage_end: date
    observed_session_dates: list[date]
    official_schedule: Literal[False] = False
    source_exchange_code: str | None
    document_id: Identifier

    @model_validator(mode="after")
    def coverage_is_ordered(self) -> "MarketCalendarCoverage":
        if self.coverage_start > self.coverage_end:
            raise ValueError("calendar coverage start must not follow end")
        if self.observed_session_dates != sorted(set(self.observed_session_dates)):
            raise ValueError("observed session dates must be sorted and unique")
        if any(
            item < self.coverage_start or item > self.coverage_end
            for item in self.observed_session_dates
        ):
            raise ValueError("observed sessions must be inside calendar coverage")
        return self


class CorporateActionKind(str, Enum):
    DIVIDEND = "dividend"
    SPLIT = "split"


class CorporateAction(CanonicalModel):
    action_id: Identifier
    listing_id: Identifier
    mic: str = Field(pattern=r"^[A-Z0-9]{4}$")
    provider_symbol: Identifier
    kind: CorporateActionKind
    ex_date: date
    amount: NonnegativeDecimalString | None = None
    currency: CurrencyCode | None = None
    split_factor: NonnegativeDecimalString | None = None
    document_id: Identifier

    @model_validator(mode="after")
    def action_shape(self) -> "CorporateAction":
        if self.kind == CorporateActionKind.DIVIDEND:
            if self.amount is None or self.currency is None or self.split_factor is not None:
                raise ValueError("dividend requires amount and currency only")
            if decimal_value(self.amount) <= 0:
                raise ValueError("dividend amount must be positive")
        elif self.split_factor is None or self.amount is not None or self.currency is not None:
            raise ValueError("split requires splitFactor only")
        elif decimal_value(self.split_factor) <= 0:
            raise ValueError("split factor must be positive")
        return self


class YahooCapture(CanonicalModel):
    capability: Literal["prices", "session", "calendar", "actions"]
    provider_label: Literal["Yahoo Finance via yfinance"]
    document: Document
    prices: list[MarketPrice] = Field(default_factory=list)
    sessions: list[MarketSession] = Field(default_factory=list)
    calendars: list[MarketCalendarCoverage] = Field(default_factory=list)
    actions: list[CorporateAction] = Field(default_factory=list)

    @model_validator(mode="after")
    def capability_shape(self) -> "YahooCapture":
        fields = {
            "prices": self.prices,
            "session": self.sessions,
            "calendar": self.calendars,
            "actions": self.actions,
        }
        if any(values for name, values in fields.items() if name != self.capability):
            raise ValueError("Yahoo capture data must match its capability")
        return self
