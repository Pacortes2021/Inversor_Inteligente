"""Tests de proyecciones EPS: growth grid, cross-check StockAnalysis,
FRED (bono 10y) y fallback de precios Nasdaq."""

import pandas as pd

from backend import data as D
from backend import estimates as EST


# --------------------------------------------------------------- SA parser

SA_HTML = """
<table class="tbl">
<tr><td>Fiscal Year</td><td>FY 2023</td><td>FY 2024</td><td>FY 2025</td><td>FY 2026</td><td>FY 2027</td></tr>
<tr><td>Period Ending</td><td>Sep 30, 2023</td><td>Sep 28, 2024</td><td>Sep 27, 2025</td><td>Sep 30, 2026</td><td>Sep 30, 2027</td></tr>
<tr><td>EPS</td><td>3.24</td><td>4.10</td><td>5.02</td><td>5.91</td><td>Upgrade</td></tr>
<tr><td>EPS Growth</td><td>10.2%</td><td>26.5%</td><td>22.4%</td><td>17.7%</td><td>Upgrade</td></tr>
<tr><td>No. Analysts</td><td>-</td><td>-</td><td>-</td><td>27</td><td>Upgrade</td></tr>
</table>
"""

SA_HTML_PAYWALL = """
<table class="tbl">
<tr><td>Fiscal Year</td><td>FY 2023</td><td>FY 2024</td><td>FY 2025</td><td>FY 2026</td><td>FY 2027</td></tr>
<tr><td>EPS</td><td>3.24</td><td>4.10</td><td>5.02</td><td>Upgrade</td><td>Upgrade</td></tr>
<tr><td>EPS Growth</td><td>10.2%</td><td>26.5%</td><td>22.4%</td><td>Upgrade</td><td>Upgrade</td></tr>
</table>
"""


def test_parse_sa_forecast():
    out = EST._parse_sa_forecast(SA_HTML)
    assert out["eps"] == 5.91
    assert out["growth"] == 17.7
    assert out["year"] == "FY 2026"
    assert out["analysts"] == 27


def test_parse_sa_forecast_paywall_skips():
    # Último dato numérico fuera del bloque de proyección (todo paywalled)
    assert EST._parse_sa_forecast(SA_HTML_PAYWALL) is None


def test_sa_eps_forecast_cache(monkeypatch):
    calls = {"n": 0}

    def fake_get(url, **kwargs):
        calls["n"] += 1
        assert "stockanalysis.com" in url

        class R:
            status_code = 200
            text = SA_HTML

        return R()

    monkeypatch.setattr("requests.get", fake_get)
    monkeypatch.setattr(EST, "cache_get", lambda k: None)
    monkeypatch.setattr(EST, "cache_set", lambda k, v, ttl: None)

    out = EST._sa_eps_forecast("TEST")
    assert out["eps"] == 5.91
    out2 = EST._sa_eps_forecast("TEST")
    assert out2["eps"] == 5.91
    assert calls["n"] == 2  # caché deshabilitada en test: una llamada por invocación


def test_sa_url_symbol():
    assert EST._sa_url_symbol("BRK-B") == "brk-b"
    assert EST._sa_url_symbol("BF.B") == "bf-b"
    assert EST._sa_url_symbol("AAPL") == "aapl"


# ------------------------------------------------------------ growth grid


class FakeRaw:
    def __init__(self, g1y, g2y=None):
        idx = ["0y", "+1y"] if g2y is None else ["0y", "+1y", "+2y"]
        rows = {"growth": [None, g1y] + ([g2y] if g2y is not None else [])}
        self.earnings_estimate = pd.DataFrame(rows, index=idx)
        rows_r = {"growth": [None, 0.08, 0.06]}
        self.revenue_estimate = pd.DataFrame(rows_r, index=["0y", "+1y", "+2y"])


def _annuals():
    return [
        {"year": y, "revenue": 1000 * 1.1 ** (y - 2019), "netIncome": 100 * 1.1 ** (y - 2019),
         "eps": 1.0 * 1.1 ** (y - 2019), "fcf": 80 * 1.1 ** (y - 2019),
         "ebitda": 150 * 1.1 ** (y - 2019), "dividendPS": 0.1, "opMargin": 20}
        for y in range(2019, 2024)
    ]


def _info(**kw):
    base = {"currency": "USD", "currentPrice": 100.0, "trailingPE": 20.0,
            "forwardPE": 18.0, "sharesOutstanding": 100e6}
    base.update(kw)
    return base


def test_grid_caps_long_growth(monkeypatch):
    monkeypatch.setattr(EST, "_sa_eps_forecast", lambda s: None)
    grid = EST._build_growth_grid("X", FakeRaw(0.60, 0.55), _info(), _annuals(), 100.0)
    eps = next(r for r in grid["rows"] if r["label"] == "EPS")
    # +1y = 60% (año 1), largo = media(60,55)*0.85 = 48.9% -> techo 35%
    last_hist = eps["values"][-6]  # 2023 (histórico, último real)
    assert eps["values"][-1] > last_hist * (1.35) ** 4 * 0.9
    assert eps["values"][-1] < last_hist * (1.40) ** 5
    assert grid["epsSources"] == {"yahooGrowth": 60.0, "saGrowth": None, "saYear": None, "conflict": False, "fmp": False}


def test_grid_mean_1y_2y(monkeypatch):
    monkeypatch.setattr(EST, "_sa_eps_forecast", lambda s: None)
    grid = EST._build_growth_grid("X", FakeRaw(0.20, 0.10), _info(), _annuals(), 100.0)
    eps = next(r for r in grid["rows"] if r["label"] == "EPS")
    last_hist = eps["values"][-6]
    esperado = last_hist * 1.20 * (1 + 0.1275) ** 4  # media(20,10)*0.85 = 12.75%
    assert abs(eps["values"][-1] - esperado) / esperado < 0.02


def test_grid_conflict_prefers_sa(monkeypatch):
    monkeypatch.setattr(EST, "_sa_eps_forecast", lambda s: {"eps": 5.0, "growth": 5.0, "year": "FY 2026", "analysts": 10})
    grid = EST._build_growth_grid("X", FakeRaw(0.30), _info(), _annuals(), 100.0)
    # Yahoo 30% vs SA 5% -> divergencia >50% relativo -> usar SA, marcar conflicto
    eps = next(r for r in grid["rows"] if r["label"] == "EPS")
    last_hist = eps["values"][-6]
    esperado = last_hist * 1.05 * (1 + 0.0425) ** 4  # año1 5%, luego 5%*0.85
    assert abs(eps["values"][-1] - esperado) / esperado < 0.02
    assert grid["epsSources"]["conflict"] is True
    assert grid["epsSources"]["saGrowth"] == 5.0


def test_grid_no_conflict_within_tolerance(monkeypatch):
    monkeypatch.setattr(EST, "_sa_eps_forecast", lambda s: {"eps": 5.0, "growth": 12.0, "year": "FY 2026", "analysts": 10})
    grid = EST._build_growth_grid("X", FakeRaw(0.10), _info(), _annuals(), 100.0)
    assert grid["epsSources"]["conflict"] is False
    assert grid["epsSources"]["saGrowth"] == 12.0


def test_grid_split_guard_bidireccional(monkeypatch):
    monkeypatch.setattr(EST, "_sa_eps_forecast", lambda s: None)
    # EDGAR sin ajustar: EPS 0.10 con precio 100 y PE 20 -> esperado 5.0 (50x)
    ann = _annuals()
    for a in ann:
        a["eps"] = 0.10 * 1.1 ** (a["year"] - 2019)
    grid = EST._build_growth_grid("X", FakeRaw(0.10), _info(), ann, 100.0)
    eps = next(r for r in grid["rows"] if r["label"] == "EPS")
    # La serie debe re-escalarse a ~5.0 (factor 50 -> redondeado 50)
    assert abs(eps["values"][-6] - 5.0) < 0.6


# --------------------------------------------------------------- FRED bond


def _fred_df():
    return pd.DataFrame({"observation_date": ["2026-07-28", "2026-07-29", "2026-07-30"],
                         "DGS10": [4.61, 4.67, 4.68]})


def test_bond_yield_fred_primary(monkeypatch):
    monkeypatch.setattr(D, "cache_get", lambda k: None)
    monkeypatch.setattr(D, "cache_set", lambda k, v, ttl: None)
    monkeypatch.setattr(pd, "read_csv", lambda url, **kw: _fred_df())
    monkeypatch.setattr(D, "safe_download", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no debe llamar a Yahoo")))
    assert D.bond_yield_10y() == 4.68


def test_bond_yield_fallback_tnx(monkeypatch):
    monkeypatch.setattr(D, "cache_get", lambda k: None)
    monkeypatch.setattr(D, "cache_set", lambda k, v, ttl: None)
    monkeypatch.setattr(pd, "read_csv", lambda url, **kw: (_ for _ in ()).throw(AssertionError("FRED caído")))
    h = pd.DataFrame({"Close": [4.2, 4.3]}, index=pd.to_datetime(["2026-07-29", "2026-07-30"]))
    monkeypatch.setattr(D, "safe_download", lambda *a, **k: h)
    assert D.bond_yield_10y() == 4.3


def test_bond_yield_fallback_default(monkeypatch):
    monkeypatch.setattr(D, "cache_get", lambda k: None)
    monkeypatch.setattr(D, "cache_set", lambda k, v, ttl: None)
    monkeypatch.setattr(pd, "read_csv", lambda url, **kw: (_ for _ in ()).throw(AssertionError("FRED caído")))
    monkeypatch.setattr(D, "safe_download", lambda *a, **k: None)
    assert D.bond_yield_10y() == 4.3


# ------------------------------------------------------------- Nasdaq history


def _nasdaq_payload():
    return {"data": {"tradesTable": {"rows": [
        {"date": "05/29/2026", "close": "$312.06", "volume": "70,026,750",
         "open": "$311.78", "high": "$315.00", "low": "$309.53"},
        {"date": "05/28/2026", "close": "$312.51", "volume": "48,220,390",
         "open": "$310.68", "high": "$312.80", "low": "$309.57"},
    ]}}, "status": {"rCode": 200}}


def test_nasdaq_history_parse(monkeypatch):
    monkeypatch.setattr(D, "cache_get", lambda k: None)
    monkeypatch.setattr(D, "cache_set", lambda k, v, ttl: None)

    class R:
        status_code = 200

        def json(self):
            return _nasdaq_payload()

    def fake_get(url, **kw):
        assert "api.nasdaq.com" in url
        assert kw["headers"].get("Referer") == "https://www.nasdaq.com/"
        return R()

    monkeypatch.setattr("requests.get", fake_get)
    df = D.nasdaq_history("AAPL", "2026-05-01", "2026-05-31")
    assert len(df) == 2
    assert df["Close"].iloc[-1] == 312.06
    assert df["Open"].iloc[-1] == 311.78
    assert df["Volume"].iloc[-1] == 70026750


def test_nasdaq_history_monthly_resample(monkeypatch):
    monkeypatch.setattr(D, "cache_get", lambda k: None)
    monkeypatch.setattr(D, "cache_set", lambda k, v, ttl: None)

    class R:
        status_code = 200

        def json(self):
            return _nasdaq_payload()

    monkeypatch.setattr("requests.get", lambda url, **kw: R())
    df = D.nasdaq_history("AAPL", "2026-05-01", "2026-05-31", interval="1mo")
    assert len(df) == 1
    assert df["Close"].iloc[0] == 312.06  # cierre del último día del mes


def test_price_history_falls_back_to_nasdaq(monkeypatch):
    monkeypatch.setattr(D, "cache_get", lambda k: None)
    monkeypatch.setattr(D, "cache_set", lambda k, v, ttl: None)
    monkeypatch.setattr(D, "safe_download", lambda *a, **k: None)

    class R:
        status_code = 200

        def json(self):
            return _nasdaq_payload()

    monkeypatch.setattr("requests.get", lambda url, **kw: R())
    df = D.price_history("AAPL", period="3mo")
    assert df is not None and len(df) == 2
