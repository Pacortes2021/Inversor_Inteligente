from __future__ import annotations

from datetime import date
from pathlib import Path
import json

import pytest

from backend.v2.domain import Fact
from backend.v2.engines.periods import (
    align_split_adjusted_comparative,
    derive_ttm_bridge,
    derive_ttm_from_quarters,
    ordered_period_values,
)


EXAMPLE = Path("docs/rework/contracts/fact.example.json")


def make_fact(
    fact_id: str,
    value: str,
    *,
    start: str,
    end: str,
    label: str,
    fiscal_year: int,
    fiscal_quarter: int | None = None,
) -> Fact:
    payload = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    payload.update(
        factId=fact_id,
        value=value,
        originalValue=value,
        originalUnit="USD",
        originalScale=1,
        period={
            "kind": "duration",
            "start": start,
            "end": end,
            "label": label,
            "fiscalYear": fiscal_year,
            "fiscalQuarter": fiscal_quarter,
        },
    )
    payload["context"].update(taxonomy="us-gaap", tag="Revenue")
    payload["evidence"][0].update(documentId=None, sha256=None)
    return Fact.model_validate(payload)


def quarter(fact_id: str, value: str, fiscal_quarter: int) -> Fact:
    ranges = {
        1: ("2024-01-01", "2024-03-31"),
        2: ("2024-04-01", "2024-06-30"),
        3: ("2024-07-01", "2024-09-30"),
        4: ("2024-10-01", "2024-12-31"),
    }
    start, end = ranges[fiscal_quarter]
    return make_fact(
        fact_id,
        value,
        start=start,
        end=end,
        label="FQ",
        fiscal_year=2024,
        fiscal_quarter=fiscal_quarter,
    )


def test_a02_duplicate_and_missing_quarter_block_ttm() -> None:
    result = derive_ttm_from_quarters(
        [quarter("q1", "10", 1), quarter("q2", "20", 2), quarter("q4-a", "40", 4), quarter("q4-b", "40", 4)]
    )

    assert result.status == "blocked"
    assert result.fact is None
    assert result.gaps == ("2024-Q3",)
    assert result.duplicates == ("2024-Q4",)


def test_four_consecutive_quarters_create_typed_ttm_lineage_and_keep_losses() -> None:
    inputs = [
        quarter("q1", "100", 1),
        quarter("q2", "100", 2),
        quarter("q3", "-200", 3),
        quarter("q4", "-300", 4),
    ]

    result = derive_ttm_from_quarters(inputs)

    assert result.status == "derived"
    assert result.fact.value == "-300"
    assert result.fact.period.label == "TTM"
    assert result.fact.origin == "derived"
    assert result.fact.input_fact_ids == [fact.fact_id for fact in inputs]
    assert result.fact.transformation.kind == "period"
    assert result.fact.transformation.parameters.method == "sum_consecutive_quarters"


def test_a03_fy_ytd_bridge_is_140_and_periods_are_compatible() -> None:
    prior_fy = make_fact(
        "fy-2024", "120", start="2024-01-01", end="2024-12-31", label="FY", fiscal_year=2024
    )
    current_ytd = make_fact(
        "ytd-2025", "100", start="2025-01-01", end="2025-09-30", label="YTD", fiscal_year=2025
    )
    prior_ytd = make_fact(
        "ytd-2024", "80", start="2024-01-01", end="2024-09-30", label="YTD", fiscal_year=2024
    )

    result = derive_ttm_bridge(
        prior_fy=prior_fy,
        current_ytd=current_ytd,
        comparable_prior_ytd=prior_ytd,
    )

    assert result.status == "derived"
    assert result.fact.value == "140"
    assert result.fact.period.start == date(2024, 10, 1)
    assert result.fact.period.end == date(2025, 9, 30)
    assert result.fact.input_fact_ids == ["fy-2024", "ytd-2025", "ytd-2024"]
    assert result.fact.transformation.parameters.method == "fy_ytd_bridge"


def test_ytd_bridge_blocks_a_noncomparable_prior_window() -> None:
    prior_fy = make_fact(
        "fy-2024", "120", start="2024-01-01", end="2024-12-31", label="FY", fiscal_year=2024
    )
    current_ytd = make_fact(
        "ytd-2025", "100", start="2025-01-01", end="2025-09-30", label="YTD", fiscal_year=2025
    )
    short_prior_ytd = make_fact(
        "ytd-2024-short", "80", start="2024-01-01", end="2024-06-30", label="YTD", fiscal_year=2024
    )

    result = derive_ttm_bridge(
        prior_fy=prior_fy,
        current_ytd=current_ytd,
        comparable_prior_ytd=short_prior_ytd,
    )

    assert result.status == "blocked"
    assert result.reason == "incompatible_fiscal_periods"


def test_a06_already_split_adjusted_comparative_is_not_adjusted_again() -> None:
    fact = make_fact(
        "eps-comparative", "2", start="2024-01-01", end="2024-12-31", label="FY", fiscal_year=2024
    )
    payload = fact.model_dump(mode="json", by_alias=True)
    payload.update(unit="money_per_share", concept="eps.diluted")
    payload["context"].update(shareBasis="split_adjusted", shareBasisId="split-basis-2025")
    adjusted = Fact.model_validate(payload)

    result = align_split_adjusted_comparative(
        adjusted, target_share_basis_id="split-basis-2025"
    )

    assert result is adjusted
    assert result.value == "2"
    assert result.transformation is None


def test_a10_complete_series_retains_negative_years() -> None:
    values = ["100", "100", "100", "-200", "-300"]
    facts = [
        make_fact(
            f"fy-{year}",
            value,
            start=f"{year}-01-01",
            end=f"{year}-12-31",
            label="FY",
            fiscal_year=year,
        )
        for year, value in zip(range(2020, 2025), values, strict=True)
    ]

    assert ordered_period_values(facts) == tuple(values)
