"""Deterministic legacy characterization. These are not v2 acceptance tests."""

from __future__ import annotations

import pandas as pd
import pytest

from backend import metrics
from backend import valuation


pytestmark = pytest.mark.characterization


def test_legacy_reverse_returns_lower_bound_for_an_inactive_growth_parameter() -> None:
    forward = [1100.0, 1210.0]
    value_low = valuation.dcf_fair_value(
        1000.0, 100.0, growth=-0.20, discount=0.10, terminal=0.025, years=2, forward_fcf=forward
    )
    value_high = valuation.dcf_fair_value(
        1000.0, 100.0, growth=0.60, discount=0.10, terminal=0.025, years=2, forward_fcf=forward
    )
    assert value_low == value_high
    assert valuation.implied_growth(
        value_low, 1000.0, 100.0,
        discount=0.10, terminal=0.025, years=2, forward_fcf=forward
    ) == -0.20


def test_legacy_ttm_accepts_a_gap_and_duplicate_as_four_records() -> None:
    columns = [
        pd.Timestamp("2024-03-31"),
        pd.Timestamp("2024-06-30"),
        pd.Timestamp("2024-12-31"),
        pd.Timestamp("2025-03-31"),
    ]
    quarterly = pd.DataFrame([[1.0, 2.0, 4.0, 5.0]], index=["Revenue"], columns=columns)
    result = metrics.ttm_from_statements(None, quarterly, "Revenue")
    assert result is not None
    assert result.iloc[-1] == 12.0
