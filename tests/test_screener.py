"""Tests para las funciones del Screener (rápido y scoring)."""

from backend import screener as S


def test_score_stock_valid():
    info = {
        "currentPrice": 100.0,
        "trailingPE": 15.0,
        "forwardPE": 12.0,
        "marketCap": 1_000_000_000,
        "freeCashflow": 80_000_000,
        "returnOnEquity": 0.20,
        "profitMargins": 0.15,
        "debtToEquity": 50.0,
        "fiftyTwoWeekHigh": 120.0,
    }
    sc = S.score_stock(info)
    assert sc is not None
    assert "score" in sc
    assert 0 <= sc["score"] <= 100
    assert sc["earningsYield"] == 6.67
    assert sc["fcfYield"] == 8.0


def test_score_stock_missing_pe():
    info = {
        "currentPrice": 50.0,
        "trailingPE": None,
        "forwardPE": None,
        "marketCap": 500_000_000,
        "freeCashflow": None,
    }
    sc = S.score_stock(info)
    assert sc is None


def test_base_row_formatting():
    info = {
        "shortName": "Test Co",
        "sector": "Technology",
        "currentPrice": 150.0,
        "currency": "USD",
        "marketCap": 5_000_000_000,
        "trailingPE": 20.4,
        "forwardPE": 18.2,
        "priceToBook": 4.5,
        "returnOnEquity": 0.25,
        "profitMargins": 0.18,
        "debtToEquity": 45.0,
    }
    row = S._base_row("TEST", info)
    assert row["symbol"] == "TEST"
    assert row["name"] == "Test Co"
    assert row["roe"] == 25.0
    assert row["netMargin"] == 18.0
    assert row["debtToEquity"] == 0.45


def test_sma_last_basic():
    values = list(range(1, 221))
    assert S._sma_last(values, 200) == 120.5
    assert S._sma_last(values, 221) is None


def test_sma_last_short_series():
    assert S._sma_last([1, 2, 3], 200) is None
    assert S._sma_last([], 200) is None
    assert S._sma_last(None, 200) is None


def test_sma_last_ignores_nan():
    values = [1.0, float("nan"), 2.0] * 100
    assert S._sma_last(values, 200) == 1.5


def test_inject_sma_computes_distances(monkeypatch):
    fake_map = {
        "AAA": {"sma200d": 100.0, "sma200w": 90.0, "date": "2026-07-30"},
        "BBB": {"sma200w": 50.0},
    }
    monkeypatch.setattr(S, "_fetch_sma_batch", lambda symbols: fake_map)
    rows = [
        {"symbol": "AAA", "price": 101.0},
        {"symbol": "BBB", "price": 48.0},
        {"symbol": "CCC", "price": 10.0},
    ]
    S._inject_sma(rows)
    aaa, bbb, ccc = rows
    assert aaa["distSma200d"] == 1.0
    assert aaa["distSma200w"] == round((101.0 / 90.0 - 1) * 100, 2)
    assert aaa["smaDate"] == "2026-07-30"
    assert bbb.get("distSma200d") is None
    assert bbb["distSma200w"] == -4.0
    assert "sma200d" not in ccc and "distSma200d" not in ccc
