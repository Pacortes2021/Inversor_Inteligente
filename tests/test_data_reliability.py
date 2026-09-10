from types import SimpleNamespace

import pandas as pd

from backend import data as D
from backend import estimates as E
from backend import metrics as M
from backend import portfolio as P
from backend import ratios as R
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


def test_piotroski_does_not_reward_unknown_debt():
    assert V.piotroski_f_score([{}, {}]) == 0
    assert V.piotroski_f_score([{"totalDebt": 0}, {"totalDebt": 0}]) == 1


def test_altman_requires_real_inputs_and_uses_standard_formula():
    assert S._altman_z_score({"assets": 1000, "revenue": 800}, 500) is None
    annual = {"assets": 1000, "workingCapital": 100, "retainedEarnings": 200,
              "totalLiabilities": 400, "revenue": 800, "opMargin": 10}
    expected = 1.2 * .1 + 1.4 * .2 + 3.3 * .08 + .6 * 1.25 + .99 * .8
    assert S._altman_z_score(annual, 500) == round(expected, 2)


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
    positions = P.get_portfolio()["positions"]
    assert all(p["pctOfPortfolio"] == 100.0 and p["overConcentrated"] for p in positions)
