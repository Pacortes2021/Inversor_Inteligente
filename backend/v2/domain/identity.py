"""Issuer, instrument, listing and share-basis identity contracts."""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Annotated

from pydantic import Field, HttpUrl, model_validator

from .common import CanonicalModel, CurrencyCode, Identifier, NonnegativeDecimalString, decimal_value


# ISO 3166-1 alpha-2 structure. Membership is a provider/catalog concern in M1.
AnnotatedCountry = Annotated[str, Field(pattern=r"^[A-Z]{2}$")]


class IdentifierType(str, Enum):
    CIK = "cik"
    RUT = "rut"
    LEI = "lei"


class TypedIdentifier(CanonicalModel):
    type: IdentifierType
    value: Identifier
    source_url: HttpUrl | None = None


class Issuer(CanonicalModel):
    issuer_id: Identifier
    legal_name: Identifier
    domicile_country: AnnotatedCountry
    identifiers: list[TypedIdentifier] = Field(default_factory=list)


class InstrumentType(str, Enum):
    COMMON_STOCK = "common_stock"
    PREFERRED_STOCK = "preferred_stock"
    ADR = "adr"
    ETF = "etf"


class Instrument(CanonicalModel):
    instrument_id: Identifier
    issuer_id: Identifier
    type: InstrumentType
    share_class: str | None = None
    rights_summary: str | None = None
    isin: str | None = Field(default=None, pattern=r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")


class ListingStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class Listing(CanonicalModel):
    listing_id: Identifier
    instrument_id: Identifier
    mic: str = Field(pattern=r"^[A-Z0-9]{4}$")
    symbol: Identifier
    currency: CurrencyCode
    timezone: Identifier
    status: ListingStatus
    valid_from: date
    valid_to: date | None = None

    @model_validator(mode="after")
    def valid_range(self) -> "Listing":
        if self.valid_to is not None and self.valid_to < self.valid_from:
            raise ValueError("validTo must not precede validFrom")
        return self


class ProviderCapability(str, Enum):
    INSTRUMENTS = "instruments"
    PRICES = "prices"
    FILINGS = "filings"
    FACTS = "facts"
    ACTIONS = "actions"
    FX = "fx"
    ESTIMATES = "estimates"
    BENCHMARK = "benchmark"


class ProviderSymbol(CanonicalModel):
    provider: Identifier
    capability: ProviderCapability
    provider_symbol: Identifier
    listing_id: Identifier
    valid_from: date
    valid_to: date | None = None
    resolution_evidence_id: Identifier

    @model_validator(mode="after")
    def valid_range(self) -> "ProviderSymbol":
        if self.valid_to is not None and self.valid_to < self.valid_from:
            raise ValueError("validTo must not precede validFrom")
        return self


class DepositaryRelation(CanonicalModel):
    relation_id: Identifier
    adr_instrument_id: Identifier
    underlying_instrument_id: Identifier
    adr_shares: int = Field(gt=0)
    underlying_shares: int = Field(gt=0)
    valid_from: date
    valid_to: date | None = None
    evidence_id: Identifier

    @model_validator(mode="after")
    def coherent_relation(self) -> "DepositaryRelation":
        if self.adr_instrument_id == self.underlying_instrument_id:
            raise ValueError("ADR and underlying instruments must differ")
        if self.valid_to is not None and self.valid_to < self.valid_from:
            raise ValueError("validTo must not precede validFrom")
        return self


class ShareBasisKind(str, Enum):
    AS_REPORTED = "as_reported"
    SPLIT_ADJUSTED = "split_adjusted"
    VALUATION_COMMON_EQUIVALENT = "valuation_common_equivalent"


class ShareComponent(CanonicalModel):
    component_id: Identifier
    kind: Identifier
    shares: NonnegativeDecimalString
    treatment: str = Field(pattern=r"^(included_in_denominator|included_in_claims|excluded)$")
    evidence_id: Identifier


class ShareBasis(CanonicalModel):
    share_basis_id: Identifier
    instrument_id: Identifier
    as_of: date
    kind: ShareBasisKind
    total_shares: NonnegativeDecimalString
    components: list[ShareComponent] = Field(min_length=1)
    split_factor: NonnegativeDecimalString | None = None
    pre_action_shares: NonnegativeDecimalString | None = None
    post_action_shares: NonnegativeDecimalString | None = None
    target_date: date | None = None
    corporate_action_id: Identifier | None = None
    version: Identifier

    @model_validator(mode="after")
    def no_double_counting(self) -> "ShareBasis":
        component_ids = [component.component_id for component in self.components]
        if len(component_ids) != len(set(component_ids)):
            raise ValueError("share components must be unique")
        included = sum(
            (decimal_value(component.shares) for component in self.components if component.treatment == "included_in_denominator"),
            start=decimal_value("0"),
        )
        if included != decimal_value(self.total_shares):
            raise ValueError("totalShares must equal denominator components")
        if decimal_value(self.total_shares) <= 0:
            raise ValueError("totalShares must be positive")
        if self.kind == ShareBasisKind.SPLIT_ADJUSTED and (
            self.split_factor is None
            or self.pre_action_shares is None
            or self.post_action_shares is None
            or self.target_date is None
            or self.corporate_action_id is None
        ):
            raise ValueError(
                "split-adjusted basis requires factor, pre/post shares, target date and action"
            )
        if self.kind == ShareBasisKind.SPLIT_ADJUSTED:
            factor = decimal_value(self.split_factor)
            if factor <= 0:
                raise ValueError("splitFactor must be positive")
            if decimal_value(self.pre_action_shares) * factor != decimal_value(self.post_action_shares):
                raise ValueError("preActionShares × splitFactor must equal postActionShares")
        return self
