"""Portafolio y diario de inversión: compras reales comparadas contra el S&P 500."""

import json
import time
from pathlib import Path

import pandas as pd
import yfinance as yf

from .data import atomic_write_json, cache_get, cache_set

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
PF_FILE = DATA_DIR / "portfolio.json"

BENCHMARK = "SPY"


def _load():
    if PF_FILE.exists():
        try:
            return json.loads(PF_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def _save(items):
    atomic_write_json(PF_FILE, items)


def _history(symbol, key, ttl=6 * 3600):
    """Serie de cierres (lista [iso, close]) con caché en disco."""
    cached = cache_get(key)
    if cached:
        return pd.Series({pd.Timestamp(d): v for d, v in cached})
    h = yf.Ticker(symbol).history(period="12y", interval="1d", auto_adjust=True)
    if h is None or h.empty:
        return None
    s = h["Close"].dropna()
    s.index = s.index.tz_localize(None)
    cache_set(key, [[str(i.date()), round(float(v), 4)] for i, v in s.items()], ttl=ttl)
    return s


def _price_at(series, date):
    """Cierre en la fecha dada o el día hábil siguiente más cercano."""
    if series is None:
        return None
    after = series[series.index >= pd.Timestamp(date)]
    if after.empty:
        return None
    return float(after.iloc[0])


def get_portfolio():
    items = _load()
    if not items:
        return {"positions": [], "totals": None}

    spy = _history(BENCHMARK, "_pf_spy")
    spy_now = float(spy.iloc[-1]) if spy is not None else None

    positions = []
    tot_invested = tot_value = 0.0
    tot_spy_value = 0.0
    sector_cache = {}

    for it in items:
        sym = it["symbol"]
        s = _history(sym, f"_pf_{sym.replace('/', '_').replace('.', '_')}")
        price_now = float(s.iloc[-1]) if s is not None and not s.empty else None

        # Obtener sector del ticker (con caché en disco)
        sector_key = f"_pf_sector_{sym.replace('/', '_')}"
        sector = cache_get(sector_key)
        if sector is None:
            try:
                info = yf.Ticker(sym).info
                sector = info.get("sector") or info.get("quoteType") or "Otro"
            except Exception:
                sector = "Otro"
            cache_set(sector_key, sector, ttl=86400)  # 24h

        pos = {**it}
        invested = it["price"] * it["shares"]
        pos["invested"] = invested
        pos["priceNow"] = price_now
        pos["sector"] = sector

        if price_now:
            value = price_now * it["shares"]
            ret = (price_now / it["price"] - 1) * 100
            pos["value"] = value
            pos["return"] = round(ret, 1)
            tot_invested += invested
            tot_value += value

            spy_then = _price_at(spy, it["date"]) if spy is not None else None
            if spy_then and spy_now:
                spy_ret = (spy_now / spy_then - 1) * 100
                pos["spyReturn"] = round(spy_ret, 1)
                pos["alpha"] = round(ret - spy_ret, 1)
                tot_spy_value += invested * (spy_now / spy_then)
            else:
                pos["spyReturn"] = pos["alpha"] = None
        else:
            pos["value"] = pos["return"] = pos["spyReturn"] = pos["alpha"] = None
        positions.append(pos)

    # Calcular % del portafolio y flag de concentración
    if tot_value > 0:
        for pos in positions:
            if pos.get("value") is not None:
                pct = (pos["value"] / tot_value) * 100
                pos["pctOfPortfolio"] = round(pct, 1)
                pos["overConcentrated"] = pct > 25
            else:
                pos["pctOfPortfolio"] = None
                pos["overConcentrated"] = False

    totals = None
    if tot_invested > 0:
        ret = (tot_value / tot_invested - 1) * 100
        spy_ret = (tot_spy_value / tot_invested - 1) * 100 if tot_spy_value else None
        totals = {
            "invested": round(tot_invested, 2),
            "value": round(tot_value, 2),
            "return": round(ret, 1),
            "spyReturn": round(spy_ret, 1) if spy_ret is not None else None,
            "alpha": round(ret - spy_ret, 1) if spy_ret is not None else None,
        }
    return {"positions": positions, "totals": totals}


def add_position(symbol, date, price, shares, note=""):
    items = _load()
    items.append({
        "id": int(time.time() * 1000),
        "symbol": symbol.upper().strip(),
        "date": date,
        "price": float(price),
        "shares": float(shares),
        "note": (note or "").strip()[:300],
    })
    _save(items)
    return items


def remove_position(pid: int):
    items = [it for it in _load() if it["id"] != pid]
    _save(items)
    return items
