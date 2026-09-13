from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path


MANIFEST = Path(__file__).parents[1] / "fixtures" / "manifest.json"


def cases() -> dict[str, dict]:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {case["id"]: case for case in payload["cases"]}


def test_a01_to_a14_have_independent_reasoned_oracles() -> None:
    catalog = cases()
    assert list(catalog) == [f"A{number:02d}" for number in range(1, 15)]
    assert all(case["rationale"] for case in catalog.values())
    assert all(case["status"] in {"accepted_by_contract", "oracle_frozen_pending_engine"} for case in catalog.values())
    assert catalog["A04"]["status"] == "accepted_by_contract"
    assert all(
        case["status"] == "oracle_frozen_pending_engine"
        for identifier, case in catalog.items()
        if identifier != "A04"
    )


def test_simple_oracles_are_calculated_independently() -> None:
    catalog = cases()

    a03 = catalog["A03"]
    calculated_ttm = (
        Decimal(a03["input"]["priorFy"])
        + Decimal(a03["input"]["currentYtd"])
        - Decimal(a03["input"]["comparablePriorYtd"])
    )
    assert calculated_ttm == Decimal(a03["expected"]["ttm"])

    a04 = catalog["A04"]
    canonical = Decimal(a04["input"]["originalValue"]) * a04["input"]["originalScale"]
    assert canonical == Decimal(a04["expected"]["canonicalValue"])

    a05 = catalog["A05"]
    eps_clp = Decimal(a05["input"]["epsUsd"]) * Decimal(a05["input"]["fxClpPerUsd"])
    pe = Decimal(a05["input"]["priceClp"]) / eps_clp
    assert eps_clp == Decimal(a05["expected"]["epsClp"])
    assert pe == Decimal(a05["expected"]["pe"])

    a07 = catalog["A07"]
    value, price = Decimal(a07["input"]["value"]), Decimal(a07["input"]["price"])
    assert (value - price) / value == Decimal(a07["expected"]["discountToValue"])
    assert (value - price) / price == Decimal(a07["expected"]["upsideToValue"])
    assert value * (1 - Decimal(a07["input"]["requiredDiscount"])) == Decimal(a07["expected"]["entryPrice"])
