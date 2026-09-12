from types import SimpleNamespace

import pandas as pd

from backend import data as D
from backend import currency as C
from backend import estimates as E
from backend import metrics as M
from backend import notes as N
from backend import portfolio as P
from backend import ratios as R
from backend import quality as Q
from backend import stock as S
from backend import valuation as V


def test_fcf_ttm_is_independent_of_column_order():
    annual = pd.DataFrame([[80.0]], index=["Free Cash Flow"],
                          columns=pd.to_datetime(["2025-12-31"]))
    descending = pd.DataFrame(
        [[40.0, 30.0, 20.0, 10.0]], index=["Free Cash Flow"],
        columns=pd.to_datetime(["2026-03-31", "2025-12-31", "2025-09-30", "2025-06-30"]),
    )
    result_desc = M.fcf_ttm_series(annual, descending)
    result_asc = M.fcf_ttm_series(annual, descending.sort_index(axis=1))
    pd.testing.assert_series_equal(result_desc, result_asc)
    assert result_desc.loc[pd.Timestamp("2026-03-31")] == 100.0


def test_fcf_per_share_preserves_clp_scale():
    out = R.calculate_ratios_payload(
        1000, {"currency": "CLP", "sharesOutstanding": 100}, [], None,
        None, None, None, fcf_ttm_now=100_000,
    )
    assert out["fcfPs"]["val"] == 1000.0


def test_projection_without_provider_is_labelled_as_model():
    annuals = [{"year": 2025, "eps": 5, "netIncome": 500, "revenue": 5000,
                "fcf": 400, "ebitda": 1000, "dividendPS": 1}]
    raw = SimpleNamespace(earnings_estimate=None, revenue_estimate=None)
    grid = E._build_growth_grid("TEST", raw, {"currency": "USD", "sharesOutstanding": 100}, annuals, 100)
    assert grid["epsSources"]["kind"] == "model"
    assert "Proyección propia" in grid["epsSources"]["source"]
    assert grid["epsSources"]["directYears"] == []


def test_negative_recent_fcf_disables_dcf():
    annuals = [{"year": 2021 + i, "fcf": f}
               for i, f in enumerate([100, 100, 100, -200, -300])]
    out = V.build_valuation(
        10, {"sharesOutstanding": 100, "freeCashflow": -300}, annuals, None, 4.3
    )
    assert out["dcfInputs"]["baseFcf"] is None
    assert "dcf" not in {m["id"] for m in out["models"]}


def test_annual_total_debt_is_used_by_dcf_fallback():
    out = V.build_valuation(
        10, {"sharesOutstanding": 100, "freeCashflow": 100},
        [{"year": 2025, "fcf": 100, "totalDebt": 500}], None, 4.3,
    )
    assert out["dcfInputs"]["netCash"] == -500


def test_currency_mismatch_omits_intrinsic_value():
    info = {"sharesOutstanding": 100, "freeCashflow": 100, "trailingEps": 2,
            "currency": "CLP", "financialCurrency": "USD", "_currencyMismatch": True}
    out = V.build_valuation(1000, info, [{"year": 2025, "fcf": 100}], {"median": 15}, 4.3)
    assert out["models"] == []
    assert out["marginOfSafety"] is None
    assert out["currencyMismatch"] is True


def test_chilean_financials_are_normalized_to_clp_without_converting_market_fields():
    info = {
        "currency": "CLP", "financialCurrency": "USD", "currentPrice": 9000,
        "marketCap": 900_000, "freeCashflow": 100, "totalDebt": 20,
        "trailingPE": 10, "priceToBook": 2,
    }
    fx = {"rate": 900.0, "rawRate": 900.0, "ticker": "CLP=X", "date": "2026-09-10"}
    out, meta = C.normalize_info("TEST.SN", info, fx=fx)
    assert out["currency"] == "CLP"
    assert out["reportedFinancialCurrency"] == "USD"
    assert out["financialCurrency"] == "CLP"
    assert out["freeCashflow"] == 90_000
    assert out["totalDebt"] == 18_000
    assert out["marketCap"] == 900_000
    assert out["trailingEps"] == 900
    assert out["bookValue"] == 4500
    assert out["_currencyMismatch"] is False
    assert meta["status"] == "converted"


def test_currency_conversion_failure_blocks_incompatible_calculations():
    info = {"currency": "CLP", "financialCurrency": "USD", "freeCashflow": 100}
    out, meta = C.normalize_info("TEST.SN", info, fx={})
    assert out["freeCashflow"] == 100
    assert out["_currencyMismatch"] is True
    assert meta["status"] == "unavailable"


def test_annual_conversion_preserves_shares_and_market_dividend():
    conversion = {"status": "converted", "source": "USD", "target": "CLP", "rate": 900.0}
    rows = [{"year": 2025, "revenue": 100, "eps": 2, "sharesOut": 50, "dividendPS": 30}]
    out = C.convert_annuals(rows, conversion)
    assert out[0]["revenue"] == 90_000
    assert out[0]["eps"] == 1800
    assert out[0]["sharesOut"] == 50
    assert out[0]["dividendPS"] == 30


def test_screener_does_not_use_fcf_yield_when_currency_is_unresolved():
    from backend import screener

    info = {
        "currentPrice": 1000, "trailingPE": 10, "marketCap": 100_000,
        "freeCashflow": 100, "_currencyMismatch": True,
    }
    assert screener.score_stock(info)["fcfYield"] is None


def test_screener_drawdown_is_context_and_does_not_raise_score():
    from backend import screener

    base = {
        "currentPrice": 100, "trailingPE": 15, "forwardPE": 14,
        "marketCap": 10_000, "freeCashflow": 600,
        "returnOnEquity": 0.18, "profitMargins": 0.15,
        "debtToEquity": 50, "revenueGrowth": 0.08,
        "earningsGrowth": 0.10, "beta": 1.0,
    }
    near_high = screener.score_stock({**base, "fiftyTwoWeekHigh": 105})
    deep_drop = screener.score_stock({**base, "fiftyTwoWeekHigh": 200})
    assert near_high["score"] == deep_drop["score"]
    assert near_high["drawdown"] != deep_drop["drawdown"]
    assert deep_drop["portfolioFitPending"] is True


def test_investment_thesis_fields_are_persisted_and_weight_is_bounded(tmp_path, monkeypatch):
    monkeypatch.setattr(N, "NOTES_FILE", tmp_path / "notes.json")
    saved = N.set_note(
        "MSFT", thesis="Tesis", risks="Riesgos", moats=["red", "inventado"],
        business="Suscripciones", growth_drivers="Azure", buy_signals="Mejor FCF",
        invalidation="Pérdida de clientes", max_weight_pct=120,
    )
    assert saved["business"] == "Suscripciones"
    assert saved["growthDrivers"] == "Azure"
    assert saved["buySignals"] == "Mejor FCF"
    assert saved["invalidation"] == "Pérdida de clientes"
    assert saved["maxWeightPct"] == 100.0
    assert saved["moats"] == ["red"]


def test_quality_warning_labels_chilean_fair_value_in_clp():
    warnings = Q.build_warnings(
        {"currency": "CLP", "financialCurrency": "CLP"}, [],
        {"marginOfSafety": -25, "consensus": 14_142, "dcfInputs": {}}, [], None,
    )
    assert any("CLP 14,142" in warning for warning in warnings)
    assert not any("($" in warning for warning in warnings)


def test_piotroski_does_not_reward_unknown_debt():
    assert V.piotroski_f_score([{}, {}]) is None
    assert V.piotroski_f_score([{"totalDebt": 0}, {"totalDebt": 0}]) == 1


def test_piotroski_reports_coverage_instead_of_treating_missing_data_as_failures():
    out = V.piotroski_f_score_details([
        {"netIncome": -10, "ocf": 20},
        {"netIncome": 15, "ocf": 25},
    ])
    assert out == {"score": 3, "evaluated": 3, "total": 9}


def test_altman_requires_real_inputs_and_uses_standard_formula():
    assert S._altman_z_score({"assets": 1000, "revenue": 800}, 500) is None
    annual = {"assets": 1000, "workingCapital": 100, "retainedEarnings": 200,
              "totalLiabilities": 400, "revenue": 800, "opMargin": 10}
    expected = 1.2 * .1 + 1.4 * .2 + 3.3 * .08 + .6 * 1.25 + .99 * .8
    assert S._altman_z_score(annual, 500) == round(expected, 2)


def test_altman_classic_is_not_applied_to_financial_companies():
    assert S._altman_applicable({"sector": "Financial Services", "industry": "Banks"}) is False
    assert S._altman_applicable({"sector": "Technology", "industry": "Software"}) is True


def test_price_history_normalizes_single_ticker_multiindex():
    df = pd.DataFrame(
        [[100.0, 10]], index=pd.to_datetime(["2026-01-02"]),
        columns=pd.MultiIndex.from_tuples([("Close", "SPY"), ("Volume", "SPY")]),
    )
    out = D.normalize_price_history(df, "SPY")
    assert list(out.columns) == ["Close", "Volume"]
    assert out["Close"].iloc[0] == 100.0


def test_raw_data_refresh_reaches_provider(monkeypatch):
    from backend.providers import factory

    seen = {}

    def fake_fetch(symbol, refresh=False):
        seen.update(symbol=symbol, refresh=refresh)
        return {"prices": pd.DataFrame({"Close": [1.0]})}

    monkeypatch.setattr(factory, "fetch_data_with_fallback", fake_fetch)
    raw = D.RawData("TEST", refresh=True)
    assert raw.is_valid()
    assert seen == {"symbol": "TEST", "refresh": True}


def test_portfolio_converts_clp_and_aggregates_symbol_concentration(monkeypatch):
    items = [
        {"id": 1, "symbol": "US", "date": "2026-01-02", "price": 100, "shares": 1, "currency": "USD"},
        {"id": 2, "symbol": "CL.SN", "date": "2026-01-02", "price": 100_000, "shares": 1, "currency": "CLP"},
    ]
    dates = pd.to_datetime(["2026-01-02", "2026-09-09"])
    histories = {
        "SPY": pd.Series([100, 100], index=dates),
        "US": pd.Series([100, 110], index=dates),
        "CL.SN": pd.Series([100_000, 90_000], index=dates),
        "CLP=X": pd.Series([1000, 900], index=dates),
    }
    monkeypatch.setattr(P, "_load", lambda: items)
    monkeypatch.setattr(P, "_history", lambda symbol, *args, **kwargs: histories[symbol])
    monkeypatch.setattr(P, "_instrument_meta", lambda symbol: {"sector": "Test", "currency": "CLP" if symbol.endswith(".SN") else "USD"})
    monkeypatch.setattr(P, "_actions", lambda symbol: {"splits": pd.Series(dtype=float), "dividends": pd.Series(dtype=float)})
    out = P.get_portfolio()
    assert out["totals"]["invested"] == 200.0
    assert out["totals"]["value"] == 210.0
    assert out["totals"]["return"] == 5.0
    assert out["totals"]["currency"] == "USD"


def test_concentration_groups_multiple_purchases_of_same_symbol(monkeypatch):
    items = [{"id": i, "symbol": "ONE", "date": "2026-01-02", "price": 10,
              "shares": 1, "currency": "USD"} for i in range(5)]
    dates = pd.to_datetime(["2026-01-02", "2026-09-09"])
    series = pd.Series([10, 10], index=dates)
    monkeypatch.setattr(P, "_load", lambda: items)
    monkeypatch.setattr(P, "_history", lambda *args, **kwargs: series)
    monkeypatch.setattr(P, "_instrument_meta", lambda symbol: {"sector": "Test", "currency": "USD"})
    monkeypatch.setattr(P, "_actions", lambda symbol: {"splits": pd.Series(dtype=float), "dividends": pd.Series(dtype=float)})
    positions = P.get_portfolio()["positions"]
    assert all(p["pctOfPortfolio"] == 100.0 and p["overConcentrated"] for p in positions)


def test_portfolio_adjusts_shares_for_splits_and_includes_cash_dividends(monkeypatch):
    items = [{"id": 1, "symbol": "SPLT", "date": "2020-01-02", "price": 100,
              "shares": 10, "currency": "USD"}]
    dates = pd.to_datetime(["2020-01-02", "2026-09-09"])
    histories = {
        "SPY": pd.Series([100, 200], index=dates),
        "SPLT": pd.Series([25, 30], index=dates),
    }
    actions = {
        "splits": pd.Series([4.0], index=pd.to_datetime(["2022-06-01"])),
        "dividends": pd.Series([1.0, 0.25], index=pd.to_datetime(["2021-06-01", "2023-06-01"])),
    }
    monkeypatch.setattr(P, "_load", lambda: items)
    monkeypatch.setattr(P, "_history", lambda symbol, *args, **kwargs: histories[symbol])
    monkeypatch.setattr(P, "_instrument_meta", lambda symbol: {"sector": "Test", "currency": "USD"})
    monkeypatch.setattr(P, "_actions", lambda symbol: actions)
    out = P.get_portfolio()
    pos = out["positions"][0]
    assert pos["adjustedShares"] == 40
    assert pos["value"] == 1200
    assert pos["dividends"] == 20
    assert pos["totalValue"] == 1220
    assert pos["return"] == 22.0
    assert out["totals"]["totalValue"] == 1220
