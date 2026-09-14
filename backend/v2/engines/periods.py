"""Period compatibility checks and fully traceable TTM derivations."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Sequence

from ..domain.facts import (
    Availability,
    Fact,
    FactOrigin,
    FactPeriod,
    PeriodKind,
    PeriodLabel,
    PeriodParameters,
    PeriodTransformation,
    Reconciliation,
    TimestampPrecision,
    ValidationState,
)


@dataclass(frozen=True)
class PeriodDerivation:
    status: Literal["derived", "blocked"]
    fact: Fact | None
    reason: str | None
    gaps: tuple[str, ...] = ()
    duplicates: tuple[str, ...] = ()


_ADDITIVE_TTM_CONCEPTS = {
    "revenue",
    "operating_income",
    "net_income",
    "cash_flow.operating",
    "capex",
}


def derive_ttm_from_quarters(facts: Sequence[Fact]) -> PeriodDerivation:
    """Sum exactly four independent consecutive fiscal quarters."""

    if not facts:
        return PeriodDerivation("blocked", None, "no_quarters")
    if facts[0].concept not in _ADDITIVE_TTM_CONCEPTS:
        return PeriodDerivation("blocked", None, "nonadditive_ttm_concept")
    mismatch = _compatibility_error(facts)
    if mismatch:
        return PeriodDerivation("blocked", None, mismatch)
    quality_error = _quality_error(facts)
    if quality_error:
        return PeriodDerivation("blocked", None, quality_error)
    invalid = [
        fact
        for fact in facts
        if fact.period.kind != PeriodKind.DURATION
        or fact.period.label != PeriodLabel.FQ
        or fact.period.fiscal_year is None
        or fact.period.fiscal_quarter is None
        or fact.period.start is None
        or not 60 <= (fact.period.end - fact.period.start).days + 1 <= 120
    ]
    if invalid:
        return PeriodDerivation("blocked", None, "requires_available_fiscal_quarters")

    by_key: dict[tuple[int, int], list[Fact]] = {}
    for fact in facts:
        key = (fact.period.fiscal_year, fact.period.fiscal_quarter)
        by_key.setdefault(key, []).append(fact)
    latest = max(by_key)
    expected = tuple(_previous_quarter(latest, offset) for offset in range(3, -1, -1))
    gaps = tuple(_quarter_label(key) for key in expected if key not in by_key)
    duplicates = tuple(
        _quarter_label(key) for key in expected if len(by_key.get(key, ())) > 1
    )
    outside = [key for key in by_key if key not in expected]
    if gaps or duplicates or outside or len(facts) != 4:
        reason = "nonconsecutive_or_nonunique_quarters"
        return PeriodDerivation("blocked", None, reason, gaps, duplicates)

    ordered = [by_key[key][0] for key in expected]
    if any(
        current.period.start is None
        or current.period.start.toordinal() != previous.period.end.toordinal() + 1
        for previous, current in zip(ordered, ordered[1:])
    ):
        return PeriodDerivation("blocked", None, "noncontiguous_quarter_dates")
    elapsed_days = (ordered[-1].period.end - ordered[0].period.start).days + 1
    if not 330 <= elapsed_days <= 380:
        return PeriodDerivation("blocked", None, "invalid_ttm_window")
    value = sum((Decimal(fact.value) for fact in ordered), Decimal(0))
    result = _derived_fact(
        ordered,
        value=value,
        start=ordered[0].period.start,
        end=ordered[-1].period.end,
        fiscal_year=ordered[-1].period.fiscal_year,
        method="sum_consecutive_quarters",
    )
    return PeriodDerivation("derived", result, None)


def derive_ttm_bridge(
    *, prior_fy: Fact, current_ytd: Fact, comparable_prior_ytd: Fact
) -> PeriodDerivation:
    """Derive TTM = prior FY + current YTD - comparable prior YTD."""

    facts = [prior_fy, current_ytd, comparable_prior_ytd]
    if prior_fy.concept not in _ADDITIVE_TTM_CONCEPTS:
        return PeriodDerivation("blocked", None, "nonadditive_ttm_concept")
    mismatch = _compatibility_error(facts)
    if mismatch:
        return PeriodDerivation("blocked", None, mismatch)
    quality_error = _quality_error(facts)
    if quality_error:
        return PeriodDerivation("blocked", None, quality_error)
    if (
        prior_fy.period.label != PeriodLabel.FY
        or current_ytd.period.label != PeriodLabel.YTD
        or comparable_prior_ytd.period.label != PeriodLabel.YTD
        or prior_fy.period.fiscal_year is None
        or current_ytd.period.fiscal_year != prior_fy.period.fiscal_year + 1
        or comparable_prior_ytd.period.fiscal_year != prior_fy.period.fiscal_year
        or current_ytd.period.start is None
        or comparable_prior_ytd.period.start is None
    ):
        return PeriodDerivation("blocked", None, "incompatible_fiscal_periods")
    if prior_fy.period.start != comparable_prior_ytd.period.start:
        return PeriodDerivation("blocked", None, "incompatible_fiscal_periods")
    if (
        (current_ytd.period.start - prior_fy.period.end).days != 1
        or not _one_year_apart(comparable_prior_ytd.period.start, current_ytd.period.start)
        or not _one_year_apart(comparable_prior_ytd.period.end, current_ytd.period.end)
    ):
        return PeriodDerivation("blocked", None, "incompatible_fiscal_periods")
    if abs(
        (current_ytd.period.end - current_ytd.period.start).days
        - (comparable_prior_ytd.period.end - comparable_prior_ytd.period.start).days
    ) > 7:
        return PeriodDerivation("blocked", None, "noncomparable_ytd_windows")

    value = (
        Decimal(prior_fy.value)
        + Decimal(current_ytd.value)
        - Decimal(comparable_prior_ytd.value)
    )
    start = date.fromordinal(comparable_prior_ytd.period.end.toordinal() + 1)
    result = _derived_fact(
        facts,
        value=value,
        start=start,
        end=current_ytd.period.end,
        fiscal_year=current_ytd.period.fiscal_year,
        method="fy_ytd_bridge",
    )
    return PeriodDerivation("derived", result, None)


def align_split_adjusted_comparative(fact: Fact, *, target_share_basis_id: str) -> Fact:
    """Return an already aligned comparative unchanged; never apply a split twice."""

    if (
        fact.context.share_basis == "split_adjusted"
        and fact.context.share_basis_id == target_share_basis_id
    ):
        return fact
    raise ValueError("split adjustment requires a distinct, explicit corporate-action transform")


def ordered_period_values(facts: Sequence[Fact]) -> tuple[str, ...]:
    """Return the complete compatible history, including zeroes and losses."""

    if not facts:
        return ()
    mismatch = _compatibility_error(facts)
    if mismatch:
        raise ValueError(mismatch)
    quality_error = _quality_error(facts)
    if quality_error:
        raise ValueError(quality_error)
    values = [fact.value for fact in sorted(facts, key=lambda item: item.period.end)]
    if any(value is None for value in values):
        raise ValueError("requires_available_inputs")
    return tuple(value for value in values if value is not None)


def _compatibility_error(facts: Sequence[Fact]) -> str | None:
    first = facts[0]
    signature = _signature(first)
    if any(_signature(fact) != signature for fact in facts[1:]):
        return "incompatible_fact_contexts"
    return None


def _quality_error(facts: Sequence[Fact]) -> str | None:
    if any(fact.availability != Availability.AVAILABLE for fact in facts):
        return "requires_available_inputs"
    if any(fact.quality.validation != ValidationState.VALID for fact in facts):
        return "requires_valid_inputs"
    if any(fact.quality.reconciliation == Reconciliation.CONFLICT for fact in facts):
        return "conflicting_inputs"
    return None


def _one_year_apart(earlier: date, later: date) -> bool:
    if later.year != earlier.year + 1:
        return False
    if (earlier.month, earlier.day) == (later.month, later.day):
        return True
    return earlier.month == later.month == 2 and {earlier.day, later.day} == {28, 29}


def _signature(fact: Fact) -> tuple[object, ...]:
    return (
        fact.issuer_id,
        fact.instrument_id,
        fact.listing_id,
        fact.concept,
        fact.unit,
        fact.currency,
        fact.scale,
        fact.context.consolidated,
        tuple(sorted(fact.context.dimensions.items())),
        fact.context.taxonomy,
        fact.context.tag,
        fact.context.share_basis,
        fact.context.share_basis_id,
    )


def _derived_fact(
    inputs: Sequence[Fact],
    *,
    value: Decimal,
    start: date | None,
    end: date,
    fiscal_year: int | None,
    method: Literal["sum_consecutive_quarters", "fy_ytd_bridge"],
) -> Fact:
    if start is None:
        raise ValueError("TTM duration requires a start date")
    first = inputs[0]
    input_ids = [fact.fact_id for fact in inputs]
    digest = hashlib.sha256(
        ("|".join(input_ids) + f"|{method}|period-r10-v1").encode("utf-8")
    ).hexdigest()[:32]
    published_at = _latest_publication(inputs)
    if isinstance(published_at, datetime):
        precision = TimestampPrecision.SECOND
    elif isinstance(published_at, date):
        precision = TimestampPrecision.DATE
    else:
        precision = TimestampPrecision.UNKNOWN
    evidence = []
    evidence_keys: set[tuple[object, ...]] = set()
    for fact in inputs:
        for item in fact.evidence:
            key = (
                item.provider,
                item.document_id,
                str(item.url) if item.url else None,
                item.locator,
                item.sha256,
            )
            if key not in evidence_keys:
                evidence_keys.add(key)
                evidence.append(item)
    payload = first.model_dump(mode="json", by_alias=False)
    payload.update(
        {
            "fact_id": f"period-{digest}",
            "value": format(value, "f"),
            "original_value": None,
            "original_unit": None,
            "original_scale": None,
            "period": FactPeriod(
                kind=PeriodKind.DURATION,
                start=start,
                end=end,
                label=PeriodLabel.TTM,
                fiscalYear=fiscal_year,
                fiscalQuarter=None,
            ),
            "published_at": published_at,
            "first_seen_at": max(fact.first_seen_at for fact in inputs),
            "retrieved_at": max(fact.retrieved_at for fact in inputs),
            "timestamp_precision": precision,
            "origin": FactOrigin.DERIVED,
            "evidence": [item.model_dump(mode="json", by_alias=False) for item in evidence],
            "input_fact_ids": input_ids,
            "transformation": PeriodTransformation(
                kind="period",
                name="ttm-period-derivation",
                version="period-r10-v1",
                parameters=PeriodParameters(method=method),
                fxFactId=None,
                shareBasisId=None,
                adjustmentIds=[],
            ),
        }
    )
    return Fact.model_validate(payload)


def _latest_publication(inputs: Sequence[Fact]) -> datetime | date | None:
    publications = [fact.published_at for fact in inputs]
    if any(item is None for item in publications):
        return None
    if all(isinstance(item, datetime) for item in publications):
        return max(item for item in publications if isinstance(item, datetime))
    if all(isinstance(item, date) and not isinstance(item, datetime) for item in publications):
        return max(item for item in publications if isinstance(item, date))
    return max(
        item.date() if isinstance(item, datetime) else item
        for item in publications
        if item is not None
    )


def _previous_quarter(latest: tuple[int, int], offset: int) -> tuple[int, int]:
    year, quarter = latest
    ordinal = year * 4 + quarter - 1 - offset
    return ordinal // 4, ordinal % 4 + 1


def _quarter_label(key: tuple[int, int]) -> str:
    return f"{key[0]}-Q{key[1]}"
