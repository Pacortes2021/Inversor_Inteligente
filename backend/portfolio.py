"""Portafolio y diario de inversión: compras reales comparadas contra el S&P 500."""

import json
import math
import threading
import time
from pathlib import Path

import pandas as pd
import yfinance as yf

from .data import atomic_write_json, cache_get, cache_set, load_json, price_history

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
PF_FILE = DATA_DIR / "portfolio.json"
_pf_lock = threading.Lock()

BENCHMARK = "SPY"
BASE_CURRENCY = "USD"
FX_TO_USD = {"CLP": "CLP=X"}  # Yahoo: CLP por 1 USD


def _load():
    return load_json(PF_FILE, [])


def _save(items):
    atomic_write_json(PF_FILE, items)


def _history(symbol, key, ttl=6 * 3600):
    """Serie de cierres (lista [iso, close]) con caché en disco."""
    cached = cache_get(key)
    if cached:
        return pd.Series({pd.Timestamp(d): v for d, v in cached})
    try:
        h = yf.Ticker(symbol).history(period="12y", interval="1d", auto_adjust=True)
        if h is None or h.empty:
            h = None
    except Exception:
        h = None
    if h is None:
        h = price_history(symbol, period="12y", interval="1d")
    if h is None or h.empty:
        return None
    s = h["Close"].dropna()
    s.index = s.index.tz_localize(None) if getattr(s.index, "tz", None) is not None else s.index
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


def _instrument_meta(symbol):
    """Sector y moneda de cotización, cacheados juntos."""
    key = f"_pf_meta_{symbol.replace('/', '_').replace('.', '_')}"
    cached = cache_get(key)
    if isinstance(cached, dict):
        return cached
    try:
        info = yf.Ticker(symbol).info or {}
    except Exception:
        info = {}
    meta = {
        "sector": info.get("sector") or info.get("quoteType") or "Otro",
        "currency": (info.get("currency") or ("CLP" if symbol.upper().endswith(".SN") else "USD")).upper(),
    }
    cache_set(key, meta, ttl=86400)
    return meta


def _fx_to_usd(currency, fx_cache):
    """Serie de unidades de moneda local por USD; USD equivale a 1."""
    currency = (currency or "").upper()
    if currency == BASE_CURRENCY:
        return None
    if currency not in FX_TO_USD:
        return None
    if currency not in fx_cache:
        fx_cache[currency] = _history(
            FX_TO_USD[currency], f"_pf_fx_{currency}_{BASE_CURRENCY}", ttl=6 * 3600
        )
    return fx_cache[currency]


def get_portfolio():
    items = _load()
    if not items:
        return {"positions": [], "totals": None}

    spy = _history(BENCHMARK, "_pf_spy")
    spy_now = float(spy.iloc[-1]) if spy is not None and not spy.empty and math.isfinite(float(spy.iloc[-1])) else None

    positions = []
    tot_invested = tot_value = 0.0
    tot_spy_value = 0.0
    fx_cache = {}
    conversion_complete = True
    benchmark_complete = True

    for it in items:
        sym = it["symbol"]
        s = _history(sym, f"_pf_{sym.replace('/', '_').replace('.', '_')}")
        price_now = float(s.iloc[-1]) if s is not None and not s.empty and math.isfinite(float(s.iloc[-1])) else None

        meta = _instrument_meta(sym)
        currency = (it.get("currency") or meta["currency"]).upper()

        pos = {**it}
        pos["currency"] = currency
        invested_native = it["price"] * it["shares"]
        pos["investedNative"] = invested_native
        pos["priceNow"] = price_now
        pos["sector"] = meta["sector"]

        if price_now:
            value_native = price_now * it["shares"]
            pos["valueNative"] = value_native
            fx = _fx_to_usd(currency, fx_cache)
            if currency == BASE_CURRENCY:
                fx_then = fx_now = 1.0
            else:
                fx_then = _price_at(fx, it["date"]) if fx is not None else None
                fx_now = float(fx.iloc[-1]) if fx is not None and not fx.empty else None

            if fx_then and fx_now:
                invested = invested_native / fx_then
                value = value_native / fx_now
                ret = (value / invested - 1) * 100
                pos["invested"] = invested
                pos["value"] = value
                pos["return"] = round(ret, 1)
                pos["fxAtPurchase"] = round(fx_then, 4)
                pos["fxNow"] = round(fx_now, 4)
                tot_invested += invested
                tot_value += value

                spy_then = _price_at(spy, it["date"]) if spy is not None else None
                if spy_then and spy_now:
                    spy_ret = (spy_now / spy_then - 1) * 100
                    pos["spyReturn"] = round(spy_ret, 1)
                    pos["alpha"] = round(ret - spy_ret, 1)
                    tot_spy_value += invested * (spy_now / spy_then)
                else:
                    benchmark_complete = False
                    pos["spyReturn"] = pos["alpha"] = None
            else:
                conversion_complete = False
                pos["invested"] = pos["value"] = pos["return"] = None
                pos["spyReturn"] = pos["alpha"] = None
        else:
            conversion_complete = False
            pos["valueNative"] = None
            pos["invested"] = pos["value"] = pos["return"] = pos["spyReturn"] = pos["alpha"] = None
        positions.append(pos)

    # Concentración por empresa agregada, aunque existan varias compras.
    if tot_value > 0:
        symbol_values = {}
        for pos in positions:
            if pos.get("value") is not None:
                symbol_values[pos["symbol"]] = symbol_values.get(pos["symbol"], 0) + pos["value"]
        for pos in positions:
            if pos.get("value") is not None:
                pct = (symbol_values[pos["symbol"]] / tot_value) * 100
                pos["pctOfPortfolio"] = round(pct, 1)
                pos["overConcentrated"] = pct > 25
            else:
                pos["pctOfPortfolio"] = None
                pos["overConcentrated"] = False

    totals = None
    if tot_invested > 0:
        ret = (tot_value / tot_invested - 1) * 100
        spy_ret = (tot_spy_value / tot_invested - 1) * 100 if benchmark_complete and tot_spy_value else None
        totals = {
            "invested": round(tot_invested, 2),
            "value": round(tot_value, 2),
            "return": round(ret, 1),
            "spyReturn": round(spy_ret, 1) if spy_ret is not None else None,
            "alpha": round(ret - spy_ret, 1) if spy_ret is not None else None,
            "currency": BASE_CURRENCY,
            "complete": conversion_complete,
        }
    warnings = []
    if not conversion_complete:
        warnings.append("Algunas posiciones no pudieron convertirse a USD y fueron excluidas de los totales.")
    if not benchmark_complete:
        warnings.append("No hay una cotización del S&P 500 posterior a alguna compra; el alfa total se omite.")
    return {"positions": positions, "totals": totals, "warnings": warnings}


def add_position(symbol, date, price, shares, note="", currency="USD"):
    with _pf_lock:
        items = _load()
        existing_ids = {it.get("id") for it in items}
        new_id = int(time.time() * 1000)
        while new_id in existing_ids:
            new_id += 1
        items.append({
            "id": new_id,
            "symbol": symbol.upper().strip(),
            "date": date,
            "price": float(price),
            "shares": float(shares),
            "currency": (currency or "USD").upper(),
            "note": (note or "").strip()[:300],
        })
        _save(items)
        return items


def remove_position(pid: int):
    with _pf_lock:
        items = [it for it in _load() if it["id"] != pid]
        _save(items)
        return items
