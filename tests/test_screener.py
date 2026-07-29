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
