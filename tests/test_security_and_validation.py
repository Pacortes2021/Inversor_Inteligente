import os
import tempfile
from pathlib import Path
import pytest
from pydantic import ValidationError

from backend.data import atomic_write_json
from backend.main import Position, WatchItem, Note, Backup
from backend.screener import run_deep_screener, _deep_states


def test_atomic_write_json():
    with tempfile.TemporaryDirectory() as tmpdir:
        target = Path(tmpdir) / "test.json"
        data = {"hello": "world", "num": 123}
        atomic_write_json(target, data)
        assert target.exists()
        import json
        read_back = json.loads(target.read_text(encoding="utf-8"))
        assert read_back == data


def test_watchitem_validation():
    # Válido
    item = WatchItem(symbol="  nvda  ", targetMos=30.0)
    assert item.symbol == "NVDA"
    assert item.targetMos == 30.0

    # Símbolo inválido
    with pytest.raises(ValidationError):
        WatchItem(symbol="DROP TABLE;--")

    # Target MOS negativo o fuera de rango
    with pytest.raises(ValidationError):
        WatchItem(symbol="AAPL", targetMos=-10)

    with pytest.raises(ValidationError):
        WatchItem(symbol="AAPL", targetMos=150)


def test_position_validation():
    # Válido
    p = Position(symbol="ko", date="2024-05-10", price=62.5, shares=10.0, note="Tesis ok")
    assert p.symbol == "KO"
    assert p.price == 62.5
    assert p.shares == 10.0

    # Precio negativo
    with pytest.raises(ValidationError):
        Position(symbol="KO", date="2024-05-10", price=-5.0, shares=10.0)

    # Cantidad negativa
    with pytest.raises(ValidationError):
        Position(symbol="KO", date="2024-05-10", price=50.0, shares=-1.0)

    # Fecha futura
    with pytest.raises(ValidationError):
        Position(symbol="KO", date="2099-01-01", price=50.0, shares=5.0)

    # Fecha inválida
    with pytest.raises(ValidationError):
        Position(symbol="KO", date="invalid-date", price=50.0, shares=5.0)


def test_backup_validation():
    b = Backup(
        version=1,
        watchlist=[{"symbol": "aapl", "targetMos": 20}],
        portfolio=[{"symbol": "msft", "date": "2024-01-01", "price": 400.0, "shares": 5.0}],
        notes={"AAPL": {"thesis": "buy"}},
    )
    assert b.watchlist[0]["symbol"] == "AAPL"
    assert b.portfolio[0]["symbol"] == "MSFT"


def test_screener_multi_universe_isolation():
    # Verificar que us y cl se registran independientemente
    res_us = run_deep_screener("us")
    res_cl = run_deep_screener("cl")
    assert res_us["universe"] == "us"
    assert res_cl["universe"] == "cl"


def test_sleep_with_jitter_no_nameerror():
    from backend.yfinance_wrapper import _sleep_with_jitter
    val = _sleep_with_jitter(0)
    assert isinstance(val, float) and val > 0


def test_screener_mos_zero_sorting():
    items = [
        {"symbol": "A", "mos": None},
        {"symbol": "B", "mos": 0.0},
        {"symbol": "C", "mos": 15.0},
        {"symbol": "D", "mos": -10.0},
    ]
    items.sort(key=lambda r: (r["mos"] is None, -(r["mos"] if r["mos"] is not None else -999)))
    assert [x["symbol"] for x in items] == ["C", "B", "D", "A"]
