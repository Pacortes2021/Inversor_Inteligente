from backend import investment as I
from backend import portfolio as P


def _annuals():
    return [
        {
            "year": 2021 + i, "revenue": 1_000 + i * 100,
            "netIncome": 120 + i * 10, "eps": 2 + i * .2,
            "fcf": 100 + i * 10, "opMargin": 18 + i * .2,
            "roic": 16 + i, "totalDebt": 200, "cash": 100,
            "interestCoverage": 10, "currentRatio": 1.5,
            "sharesOut": 100 - i, "capex": -60, "workingCapital": 80 + i * 4,
            "stockCompensation": 20,
        }
        for i in range(5)
    ]


def _valuation():
    return {
        "primaryModel": "dcf", "marginOfSafety": 30,
        "requiredMarginPct": 25, "impliedGrowth": 8,
        "impliedReturnPct": 11, "probabilityWeightedValue": 140,
        "currencyMismatch": False,
        "dcfInputs": {"baseFcf": 140, "growth": .10, "wacc": .09},
        "etfComparison": {"hurdlePct": 8, "excessReturnPct": 3},
        "scenarios": [
            {"key": "bear", "value": 80}, {"key": "base", "value": 130},
            {"key": "bull", "value": 180},
        ],
    }


def test_investment_matrix_has_exact_weights_and_honest_pending_range():
    out = I.build_investment_analysis(
        {"sector": "Technology", "industry": "Software", "beta": 1.0},
        _annuals(), _valuation(), {"vsMedian": -10}, price=100,
    )
    assert sum(category["weight"] for category in out["categories"]) == 100
    assert out["score"]["evaluatedPoints"] + (
        out["score"]["earnedMax"] - out["score"]["earnedMin"]
    ) == 100
    manual = [m for c in out["categories"] for m in c["metrics"] if m["manualKey"]]
    assert {m["manualKey"] for m in manual} == {
        "moatRating", "organicGrowthRating", "cyclicalityRating",
        "concentrationRating", "portfolioFitRating",
    }


def test_normalization_audit_exposes_stock_compensation_instead_of_hiding_it():
    out = I.build_investment_analysis(
        {"sector": "Technology", "beta": 1.0}, _annuals(), _valuation(),
        {"vsMedian": 0}, price=100,
    )
    audit = out["normalizationAudit"]
    assert audit["stockCompensation"] == 20
    assert audit["stockCompPctFcf"] == round(20 / 140 * 100, 1)
    assert audit["fcfAfterStockComp"] == 120
    assert "mantenimiento" in audit["unavailableAdjustments"][0]


def test_reit_blocks_decision_until_affo_exists():
    valuation = {**_valuation(), "primaryModel": None}
    out = I.build_investment_analysis(
        {"sector": "Real Estate", "industry": "REIT - Retail"},
        _annuals(), valuation, None, price=100,
    )
    assert out["modelReview"]["companyType"] == "reit"
    assert out["decisionReady"] is False
    assert any("AFFO" in blocker for blocker in out["blockers"])


def test_financial_company_does_not_receive_industrial_fcf_or_roic_scores():
    valuation = {**_valuation(), "primaryModel": "ddm"}
    out = I.build_investment_analysis(
        {"sector": "Financial Services", "industry": "Banks", "beta": 1.0},
        _annuals(), valuation, {"vsMedian": -10}, price=100,
    )
    metrics = {
        metric["id"]: metric
        for category in out["categories"]
        for metric in category["metrics"]
    }
    for metric_id in ("roic_wacc", "cash_conversion", "fcf_positive",
                      "debt_payback", "fcf_growth"):
        assert metrics[metric_id]["status"] == "pending"
        assert metrics[metric_id]["earnedPoints"] is None


def test_fcf_cagr_stays_pending_when_history_crosses_negative_cash_flow():
    annuals = _annuals()
    annuals[2]["fcf"] = -50
    out = I.build_investment_analysis(
        {"sector": "Technology", "industry": "Software", "beta": 1.0},
        annuals, _valuation(), {"vsMedian": 0}, price=100,
    )
    metrics = {m["id"]: m for c in out["categories"] for m in c["metrics"]}
    assert metrics["fcf_growth"]["status"] == "pending"


def test_portfolio_fit_uses_actual_sector_and_symbol_exposure(monkeypatch):
    monkeypatch.setattr(P, "get_portfolio", lambda: {"positions": [
        {"symbol": "MSFT", "sector": "Technology", "currency": "USD", "value": 60},
        {"symbol": "AAPL", "sector": "Technology", "currency": "USD", "value": 40},
    ]})
    monkeypatch.setattr(P, "_instrument_meta", lambda symbol: {"sector": "Technology", "currency": "USD"})
    out = P.get_portfolio_fit("MSFT")
    assert out["available"] is True
    assert out["symbolWeightPct"] == 60
    assert out["sectorWeightPct"] == 100
    assert out["suggestedRating"] == "weak"
