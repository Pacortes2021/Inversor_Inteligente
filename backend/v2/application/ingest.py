"""Offline ingestion of identified provider captures into an immutable US snapshot."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime

from ..adapters.persistence import (
    FactRepository,
    IdentityRepository,
    SelectionRepository,
    SnapshotRepository,
)
from ..adapters.providers.sec_mapping import SecFactMapper, SecMappingResult
from ..domain import (
    DatasetSnapshot,
    Fact,
    FactSelectionQuery,
    MarketPrice,
    SecCapture,
    SelectionDecision,
    SelectionPolicy,
    YahooCapture,
)
from ..domain.facts import (
    Availability,
    Evidence,
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
from ..domain.common import canonical_json, jsonable
from .select_facts import select_fact
from .snapshots import build_snapshot


SELECTION_POLICY_VERSION = "selection-r12-v1"
PERIOD_POLICY_VERSION = "period-r10-v1"
REQUIRED_US_CONCEPTS = {
    "revenue",
    "operating_income",
    "net_income",
    "cash_flow.operating",
    "capex",
    "cash",
    "debt.current",
    "debt.noncurrent",
    "shares.weighted_average.diluted",
    "eps.diluted",
}


@dataclass(frozen=True)
class UsSnapshotIngestResult:
    snapshot: DatasetSnapshot
    facts: tuple[Fact, ...]
    decisions: tuple[SelectionDecision, ...]
    sec_mapping: tuple[SecMappingResult, ...]


def ingest_us_snapshot(
    *,
    sec_capture: SecCapture,
    yahoo_capture: YahooCapture,
    issuer_id: str,
    instrument_id: str,
    listing_id: str,
    quote_currency: str,
    share_basis_id: str,
    as_of: datetime,
    identities: IdentityRepository,
    facts: FactRepository,
    selections: SelectionRepository,
    snapshots: SnapshotRepository,
    mapper: SecFactMapper | None = None,
) -> UsSnapshotIngestResult:
    """Persist one fully selected snapshot from already captured provider data."""

    if sec_capture.capability != "companyfacts":
        raise ValueError("US snapshot requires a SEC companyfacts capture")
    if yahoo_capture.capability != "prices":
        raise ValueError("US snapshot requires a Yahoo prices capture")
    if sec_capture.cik is None:
        raise ValueError("SEC capture must identify its filer")
    _validate_identity(
        sec_capture=sec_capture,
        yahoo_capture=yahoo_capture,
        issuer_id=issuer_id,
        instrument_id=instrument_id,
        listing_id=listing_id,
        quote_currency=quote_currency,
        share_basis_id=share_basis_id,
        identities=identities,
    )
    facts.add_document(sec_capture.document)
    facts.add_document(yahoo_capture.document)
    fact_mapper = mapper or SecFactMapper()
    mapping = tuple(
        fact_mapper.map(
            source,
            issuer_id=issuer_id,
            instrument_id=instrument_id,
            document=sec_capture.document,
        )
        for source in sec_capture.facts
    )
    sec_facts = [result.fact for result in mapping if result.status == "mapped"]
    mapped_concepts = {fact.concept for fact in sec_facts}
    missing = sorted(REQUIRED_US_CONCEPTS - mapped_concepts)
    if missing:
        blocked_reasons = sorted(
            {result.reason for result in mapping if result.status == "blocked"}
        )
        detail = f"; blocked: {', '.join(blocked_reasons)}" if blocked_reasons else ""
        raise ValueError(f"US snapshot lacks required concepts: {', '.join(missing)}{detail}")

    split_adjusted_prices = [
        item for item in yahoo_capture.prices if item.basis == "split_adjusted"
    ]
    if not split_adjusted_prices:
        raise ValueError("US snapshot requires Yahoo Close with split-adjusted semantics")
    latest_price = max(split_adjusted_prices, key=lambda item: item.session_date)
    if (
        latest_price.instrument_id != instrument_id
        or latest_price.listing_id != listing_id
        or latest_price.currency != quote_currency
    ):
        raise ValueError("Yahoo price does not match requested snapshot identity")
    price_fact = market_price_fact(latest_price, yahoo_capture)
    candidates = [*sec_facts, price_fact]
    for fact in candidates:
        facts.add_fact(fact)

    policy = SelectionPolicy(
        version=SELECTION_POLICY_VERSION,
        providerPriority=["sec", "yahoo"],
    )
    decisions = []
    selected_by_id = {}
    for group in _semantic_groups(candidates):
        fact = group[0]
        query = FactSelectionQuery(
            issuerId=fact.issuer_id,
            instrumentId=fact.instrument_id,
            listingId=fact.listing_id,
            concept=fact.concept,
            unit=fact.unit,
            currency=fact.currency,
            period=fact.period,
            context=fact.context,
            asOf=as_of,
            mode="latest_restated",
        )
        decision = select_fact(group, query, policy)
        if decision.status != "selected":
            raise ValueError(f"fact group {fact.concept} is unresolved at snapshot cutoff")
        decisions.append(selections.add(decision))
        selected_by_id[decision.selected_fact_id] = next(
            item for item in group if item.fact_id == decision.selected_fact_id
        )
    selected_facts = list(selected_by_id.values())

    snapshot = build_snapshot(
        instrument_id=instrument_id,
        listing_id=listing_id,
        quote_currency=quote_currency,
        as_of=as_of,
        decisions=decisions,
        facts=selected_facts,
        price_fact_id=price_fact.fact_id,
        fx_fact_id=None,
        share_basis_id=share_basis_id,
        selection_policy_version=policy.version,
        period_policy_version=PERIOD_POLICY_VERSION,
    )
    snapshots.add(
        snapshot,
        sorted(decision.selection_decision_id for decision in decisions),
    )
    return UsSnapshotIngestResult(
        snapshot=snapshot,
        facts=tuple(selected_facts),
        decisions=tuple(decisions),
        sec_mapping=mapping,
    )


def _semantic_groups(facts: list[Fact]) -> list[list[Fact]]:
    grouped: dict[str, list[Fact]] = {}
    for fact in facts:
        signature = canonical_json(
            {
                "issuerId": fact.issuer_id,
                "instrumentId": fact.instrument_id,
                "listingId": fact.listing_id,
                "concept": fact.concept,
                "unit": fact.unit,
                "currency": fact.currency,
                "period": jsonable(fact.period),
                "context": jsonable(fact.context),
            }
        )
        grouped.setdefault(signature, []).append(fact)
    return [grouped[key] for key in sorted(grouped)]


def _validate_identity(
    *,
    sec_capture: SecCapture,
    yahoo_capture: YahooCapture,
    issuer_id: str,
    instrument_id: str,
    listing_id: str,
    quote_currency: str,
    share_basis_id: str,
    identities: IdentityRepository,
) -> None:
    issuer = identities.get_issuer(issuer_id)
    if issuer is None or not any(
        identifier.type == "cik" and identifier.value == sec_capture.cik
        for identifier in issuer.identifiers
    ):
        raise ValueError("SEC CIK does not match persisted issuer identity")
    instrument = identities.get_instrument(instrument_id)
    if instrument is None or instrument.issuer_id != issuer_id:
        raise ValueError("instrument does not match persisted issuer identity")
    listing = identities.get_listing(listing_id)
    if (
        listing is None
        or listing.instrument_id != instrument_id
        or listing.currency != quote_currency
    ):
        raise ValueError("listing does not match persisted snapshot identity")
    basis = identities.get_share_basis(share_basis_id)
    if basis is None or basis.instrument_id != instrument_id:
        raise ValueError("share basis does not match persisted instrument")
    split_adjusted_prices = [
        item for item in yahoo_capture.prices if item.basis == "split_adjusted"
    ]
    if not split_adjusted_prices:
        raise ValueError("Yahoo capture has no split-adjusted price identity")
    latest = max(split_adjusted_prices, key=lambda item: item.session_date)
    symbol_history = identities.provider_symbol_history("yahoo", "prices", listing_id)
    valid_symbols = {
        item.provider_symbol
        for item in symbol_history
        if item.valid_from <= latest.session_date
        and (item.valid_to is None or latest.session_date <= item.valid_to)
    }
    if latest.provider_symbol not in valid_symbols or latest.mic != listing.mic:
        raise ValueError("Yahoo symbol or MIC does not match persisted listing identity")


def market_price_fact(price: MarketPrice, capture: YahooCapture) -> Fact:
    if price.document_id != capture.document.document_id:
        raise ValueError("Yahoo price and capture document do not match")
    if price.basis != "split_adjusted":
        raise ValueError("the first US snapshot uses Yahoo Close as split-adjusted")
    digest = hashlib.sha256(
        (
            f"{price.listing_id}|{price.provider_symbol}|{price.session_date}|"
            f"{price.value}|{price.basis}|{capture.document.sha256}"
        ).encode("utf-8")
    ).hexdigest()[:32]
    return Fact(
        factId=f"yahoo-price-{digest}",
        issuerId=price.issuer_id,
        instrumentId=price.instrument_id,
        listingId=price.listing_id,
        concept="price.close",
        value=price.value,
        unit=Unit.MONEY_PER_SHARE,
        currency=price.currency,
        scale=1,
        originalValue=price.value,
        originalUnit=f"{price.currency}/share",
        originalScale=1,
        period=FactPeriod(
            kind=PeriodKind.INSTANT,
            start=None,
            end=price.session_date,
            label=PeriodLabel.INSTANT,
            fiscalYear=None,
            fiscalQuarter=None,
        ),
        context=FactContext(
            consolidated=None,
            dimensions={
                "priceBasis": price.basis,
                "mic": price.mic,
                "providerSymbol": price.provider_symbol,
            },
            taxonomy="yahoo_market_data",
            tag=price.source_field,
            shareBasis=FactShareBasis.NOT_APPLICABLE,
            shareBasisId=None,
        ),
        publishedAt=price.session_date,
        firstSeenAt=capture.document.fetched_at,
        retrievedAt=capture.document.fetched_at,
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
                provider="yahoo",
                documentId=capture.document.document_id,
                url=capture.document.source_url,
                locator=(
                    f"symbol={price.provider_symbol}; session={price.session_date}; "
                    f"field={price.source_field}; basis={price.basis}; mic={price.mic}"
                ),
                sha256=capture.document.sha256,
            )
        ],
        inputFactIds=[],
        transformation=None,
    )
