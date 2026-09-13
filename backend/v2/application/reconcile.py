"""Pure comparison helpers for semantically compatible facts."""

from __future__ import annotations

from decimal import Decimal
from itertools import combinations

from ..domain.facts import Fact
from ..domain.policies import CandidateDifference, SelectionPolicy


def compare_candidates(facts: list[Fact], policy: SelectionPolicy) -> list[CandidateDifference]:
    differences: list[CandidateDifference] = []
    relative_tolerance = Decimal(policy.relative_tolerance)
    absolute_tolerance = Decimal(policy.absolute_tolerance)
    for left, right in combinations(facts, 2):
        if left.value is None or right.value is None:
            continue
        left_value = Decimal(left.value)
        right_value = Decimal(right.value)
        absolute = abs(left_value - right_value)
        denominator = max(abs(left_value), abs(right_value))
        relative = Decimal("0") if denominator == 0 else absolute / denominator
        material = absolute > absolute_tolerance and relative > relative_tolerance
        differences.append(
            CandidateDifference(
                leftFactId=left.fact_id,
                rightFactId=right.fact_id,
                absolute=format(absolute, "f"),
                relative=format(relative, "f"),
                material=material,
            )
        )
    return differences
