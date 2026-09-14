"""Versioned, explicit mapping from SEC companyfacts into canonical facts."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import date
from typing import Literal, Mapping

from ...domain.documents import Document
from ...domain.facts import (
    Availability,
    Evidence,
    Fact,
    FactContext,
    FactOrigin,
    FactPeriod,
    FactQuality,
    FactShareBasis,
    Freshness,
    PeriodKind,
    PeriodLabel,
    Reconciliation,
    TimestampPrecision,
    Unit,
    ValidationState,
)
from ...domain.sec import SecUnitFact


POLICY_VERSION = "sec-us-gaap-r10-v1"
_DURATION_FORMS = {"10-K", "10-K/A", "10-Q", "10-Q/A"}
_QUARTER_FRAME = re.compile(r"^CY[0-9]{4}Q([1-4])$")
_MONEY_PER_SHARE = re.compile(r"^([A-Z]{3})/shares$")
_CURRENCY = re.compile(r"^[A-Z]{3}$")


@dataclass(frozen=True)
class ConceptRule:
    concept: str
    tags: tuple[str, ...]
    unit: Unit


RULES = (
    ConceptRule(
        "revenue",
        ("RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues"),
        Unit.MONEY,
    ),
    ConceptRule("operating_income", ("OperatingIncomeLoss",), Unit.MONEY),
    ConceptRule("net_income", ("NetIncomeLoss", "ProfitLoss"), Unit.MONEY),
    ConceptRule(
        "cash_flow.operating",
        ("NetCashProvidedByUsedInOperatingActivities",),
        Unit.MONEY,
    ),
    ConceptRule(
        "capex",
        ("PaymentsToAcquirePropertyPlantAndEquipment",),
        Unit.MONEY,
    ),
    ConceptRule(
        "cash",
        (
            "CashAndCashEquivalentsAtCarryingValue",
            "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
        ),
        Unit.MONEY,
    ),
    ConceptRule(
        "debt.current",
        ("LongTermDebtCurrent", "ShortTermBorrowings"),
        Unit.MONEY,
    ),
    ConceptRule("debt.noncurrent", ("LongTermDebtNoncurrent",), Unit.MONEY),
    ConceptRule(
        "shares.weighted_average.basic",
        ("WeightedAverageNumberOfSharesOutstandingBasic",),
        Unit.SHARES,
    ),
    ConceptRule(
        "shares.weighted_average.diluted",
        ("WeightedAverageNumberOfDilutedSharesOutstanding",),
        Unit.SHARES,
    ),
    ConceptRule("eps.basic", ("EarningsPerShareBasic",), Unit.MONEY_PER_SHARE),
    ConceptRule("eps.diluted", ("EarningsPerShareDiluted",), Unit.MONEY_PER_SHARE),
)

_RULE_BY_TAG = {tag: rule for rule in RULES for tag in rule.tags}


@dataclass(frozen=True)
class SecMappingResult:
    status: Literal["mapped", "unsupported", "blocked"]
    policy_version: str
    source: SecUnitFact
    fact: Fact | None
    reason: str | None
    candidate_tags: tuple[str, ...]


class SecFactMapper:
    """Map only supported entity-wide US-GAAP observations without guessing."""

    def __init__(self, *, policy_version: str = POLICY_VERSION) -> None:
        self.policy_version = policy_version

    def map(
        self,
        source: SecUnitFact,
        *,
        issuer_id: str,
        document: Document,
        dimensions: Mapping[str, str] | None = None,
        instrument_id: str | None = None,
        share_basis_id: str | None = None,
        share_basis_kind: Literal["as_reported", "split_adjusted"] | None = None,
    ) -> SecMappingResult:
        if source.document_id != document.document_id:
            raise ValueError("SEC fact and source document do not match")
        if document.provider != "sec":
            raise ValueError("SEC mapping requires a SEC source document")
        if dimensions:
            return self._result(source, "blocked", "unsupported_dimensions")
        if source.taxonomy != "us-gaap":
            return self._result(source, "unsupported", "unsupported_taxonomy_extension")
        rule = _RULE_BY_TAG.get(source.tag)
        if rule is None:
            return self._result(source, "unsupported", "unmapped_tag")
        unit, currency = _canonical_unit(source.unit)
        if unit is None or unit != rule.unit:
            return self._result(
                source,
                "blocked",
                "unsupported_unit",
                candidate_tags=rule.tags,
            )
        try:
            period = _canonical_period(source)
        except ValueError as error:
            return self._result(
                source,
                "blocked",
                str(error),
                candidate_tags=rule.tags,
            )

        share_basis = FactShareBasis.NOT_APPLICABLE
        canonical_basis_id = None
        if unit in (Unit.SHARES, Unit.MONEY_PER_SHARE):
            if share_basis_id is None:
                share_basis = FactShareBasis.UNKNOWN
            elif instrument_id is None:
                return self._result(
                    source,
                    "blocked",
                    "share_basis_requires_instrument",
                    candidate_tags=rule.tags,
                )
            elif share_basis_kind is None:
                return self._result(
                    source,
                    "blocked",
                    "share_basis_kind_required",
                    candidate_tags=rule.tags,
                )
            else:
                share_basis = FactShareBasis(share_basis_kind)
                canonical_basis_id = share_basis_id

        locator = (
            f"accession={source.accession_number}; taxonomy={source.taxonomy}; "
            f"tag={source.tag}; unit={source.unit}; end={source.end.isoformat()}; "
            f"mappingPolicy={self.policy_version}"
        )
        digest = hashlib.sha256(
            (
                f"{issuer_id}|{source.cik}|{source.accession_number}|{source.taxonomy}|"
                f"{source.tag}|{source.unit}|{source.start}|{source.end}|{source.value}|"
                f"{self.policy_version}"
            ).encode("utf-8")
        ).hexdigest()[:32]
        fact = Fact(
            factId=f"sec-{digest}",
            issuerId=issuer_id,
            instrumentId=instrument_id,
            listingId=None,
            concept=rule.concept,
            value=source.value,
            unit=unit,
            currency=currency,
            scale=1,
            originalValue=source.value,
            originalUnit=source.unit,
            originalScale=1,
            period=period,
            context=FactContext(
                consolidated=True,
                dimensions={},
                taxonomy=source.taxonomy,
                tag=source.tag,
                shareBasis=share_basis,
                shareBasisId=canonical_basis_id,
            ),
            publishedAt=source.filed,
            firstSeenAt=document.fetched_at,
            retrievedAt=document.fetched_at,
            timestampPrecision=TimestampPrecision.DATE,
            origin=FactOrigin.REPORTED,
            availability=Availability.AVAILABLE,
            missingReason=None,
            quality=FactQuality(
                freshness=Freshness.UNKNOWN,
                reconciliation=Reconciliation.SINGLE_SOURCE,
                validation=ValidationState.VALID,
            ),
            evidence=[
                Evidence(
                    provider="sec",
                    documentId=document.document_id,
                    url=document.source_url,
                    locator=locator,
                    sha256=document.sha256,
                )
            ],
            inputFactIds=[],
            transformation=None,
        )
        return SecMappingResult(
            status="mapped",
            policy_version=self.policy_version,
            source=source,
            fact=fact,
            reason=None,
            candidate_tags=rule.tags,
        )

    def _result(
        self,
        source: SecUnitFact,
        status: Literal["unsupported", "blocked"],
        reason: str,
        *,
        candidate_tags: tuple[str, ...] = (),
    ) -> SecMappingResult:
        return SecMappingResult(
            status=status,
            policy_version=self.policy_version,
            source=source,
            fact=None,
            reason=reason,
            candidate_tags=candidate_tags,
        )


def _canonical_unit(raw: str) -> tuple[Unit | None, str | None]:
    if raw == "shares":
        return Unit.SHARES, None
    per_share = _MONEY_PER_SHARE.fullmatch(raw)
    if per_share:
        return Unit.MONEY_PER_SHARE, per_share.group(1)
    if _CURRENCY.fullmatch(raw):
        return Unit.MONEY, raw
    return None, None


def _canonical_period(source: SecUnitFact) -> FactPeriod:
    if source.start is None:
        return FactPeriod(
            kind=PeriodKind.INSTANT,
            start=None,
            end=source.end,
            label=PeriodLabel.INSTANT,
            fiscalYear=source.fiscal_year,
            fiscalQuarter=None,
        )
    if source.form not in _DURATION_FORMS:
        raise ValueError("unsupported_filing_form")
    match = _QUARTER_FRAME.fullmatch(source.frame or "")
    elapsed_days = (source.end - source.start).days + 1
    if match and elapsed_days <= 120:
        label = PeriodLabel.FQ
        quarter = int(match.group(1))
    elif source.fiscal_period == "FY" and source.form.startswith("10-K"):
        label = PeriodLabel.FY
        quarter = None
    elif source.fiscal_period in {"Q1", "Q2", "Q3", "Q4"}:
        label = PeriodLabel.YTD
        quarter = None
    else:
        raise ValueError("unsupported_period_context")
    return FactPeriod(
        kind=PeriodKind.DURATION,
        start=source.start,
        end=source.end,
        label=label,
        fiscalYear=source.fiscal_year,
        fiscalQuarter=quarter,
    )


def policy_candidates(concept: str) -> tuple[str, ...]:
    """Expose ordered aliases so mapping decisions remain reviewable."""

    rule = next((item for item in RULES if item.concept == concept), None)
    return () if rule is None else rule.tags
