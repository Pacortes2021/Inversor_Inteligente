"""Datos de mercado para el dashboard: índices, sobrevendidas, top movers."""

import math
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import yfinance as yf

from .data import TTL_SCREENER, bond_yield_10y, cache_get, cache_set, jclean
from .screener import UNIVERSE_US


def _calc_rsi(closes, period=14):
    """RSI 14 de una serie de precios."""
    if len(closes) < period + 1:
        return None
    delta = closes.diff()
    gain = delta.where(delta > 0, 0.0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    val = rsi.iloc[-1]
    return round(float(val), 1) if math.isfinite(val) else None


def get_indices():
    """Índices principales con sparkline de 3 meses."""
    cached = cache_get("_dash_indices")
    if cached:
        return cached

    tickers = {
        "^GSPC": {"name": "S&P 500", "icon": "📊"},
        "^IXIC": {"name": "Nasdaq", "icon": "💻"},
        "^VIX": {"name": "VIX", "icon": "⚠️"},
    }
    bond = bond_yield_10y()

    try:
        df = yf.download(list(tickers.keys()), period="3mo", interval="1d",
                         progress=False, auto_adjust=True)["Close"]
        out = []
        for sym, meta in tickers.items():
            if sym not in df.columns:
                continue
            closes = df[sym].dropna()
            if len(closes) < 2:
                continue
            price = float(closes.iloc[-1])
            prev = float(closes.iloc[-2])
            chg = round((price / prev - 1) * 100, 2)
            out.append({
                "symbol": sym,
                "name": meta["name"],
                "icon": meta["icon"],
                "price": round(price, 2),
                "changePct": chg,
                "spark": [round(float(v), 3) for v in closes.tolist()[-30:]],
            })
        out.append({
            "symbol": "^TNX",
            "name": "Bono 10Y",
            "icon": "🏦",
            "price": round(bond, 2),
            "changePct": None,
            "spark": [],
        })
        payload = jclean({"indices": out, "updatedAt": int(time.time() * 1000)})
        cache_set("_dash_indices", payload, ttl=600)
        return payload
    except Exception:
        return {"indices": [], "updatedAt": int(time.time() * 1000)}


def get_oversold():
    """Acciones con RSI < 30 del universo US (máx 8)."""
    cached = cache_get("_dash_oversold")
    if cached:
        return cached

    results = []

    def _scan(sym):
        try:
            t = yf.Ticker(sym)
            h = t.history(period="3mo", interval="1d", auto_adjust=True)
            if h is None or h.empty or len(h) < 20:
                return None
            closes = h["Close"].dropna()
            rsi = _calc_rsi(closes)
            if rsi is None or rsi >= 30:
                return None
            price = float(closes.iloc[-1])
            prev = float(closes.iloc[-2])
            chg = round((price / prev - 1) * 100, 2)
            info = {}
            try:
                info = t.info or {}
            except Exception:
                pass
            return {
                "symbol": sym,
                "name": info.get("shortName") or sym,
                "price": round(price, 2),
                "changePct": chg,
                "rsi": rsi,
                "sector": info.get("sector"),
            }
        except Exception:
            return None

    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(_scan, s): s for s in UNIVERSE_US}
        for fut in as_completed(futures):
            r = fut.result()
            if r:
                results.append(r)

    results.sort(key=lambda x: x["rsi"])
    payload = jclean({"items": results[:8], "updatedAt": int(time.time() * 1000)})
    cache_set("_dash_oversold", payload, ttl=900)
    return payload


def get_movers():
    """Top ganadores y perdedores del día del universo US."""
    cached = cache_get("_dash_movers")
    if cached:
        return cached

    try:
        df = yf.download(UNIVERSE_US, period="5d", interval="1d",
                         progress=False, auto_adjust=True)["Close"]
        results = []
        for sym in UNIVERSE_US:
            if sym not in df.columns:
                continue
            closes = df[sym].dropna()
            if len(closes) < 2:
                continue
            price = float(closes.iloc[-1])
            prev = float(closes.iloc[-2])
            chg = round((price / prev - 1) * 100, 2)
            results.append({"symbol": sym, "price": round(price, 2), "changePct": chg})

        results.sort(key=lambda x: x["changePct"], reverse=True)
        gainers = results[:5]
        losers = results[-5:][::-1]
        losers.sort(key=lambda x: x["changePct"])

        payload = jclean({
            "gainers": gainers,
            "losers": losers,
            "updatedAt": int(time.time() * 1000),
        })
        cache_set("_dash_movers", payload, ttl=600)
        return payload
    except Exception:
        return {"gainers": [], "losers": [], "updatedAt": int(time.time() * 1000)}
