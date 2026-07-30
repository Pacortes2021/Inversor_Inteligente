"""Watchlist persistente con margen de seguridad objetivo por acción."""

import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .data import atomic_write_json, bond_yield_10y
from .screener import scan_one_deep

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
WL_FILE = DATA_DIR / "watchlist.json"


def _load():
    if WL_FILE.exists():
        try:
            return json.loads(WL_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def _save(items):
    atomic_write_json(WL_FILE, items)


def get_watchlist():
    """Lista con evaluación actual, rendimiento, RSI y más."""
    items = _load()
    if not items:
        return {"items": []}
    
    import yfinance as yf
    import pandas as pd
    bond10y = bond_yield_10y()
    
    symbols = [it["symbol"] for it in items]
    df = yf.download(symbols, period="1y", group_by="ticker", auto_adjust=True, progress=False)

    def evaluate(item):
        sym = item["symbol"]
        row = scan_one_deep(sym, bond10y)
        out = {**item}
        
        # Rendimiento y RSI
        perf = {"1D": None, "5D": None, "1M": None, "1Y": None, "RSI": None}
        if len(symbols) == 1:
            d = df
        else:
            d = df[sym] if sym in df.columns.levels[0] else None
            
        if d is not None and "Close" in d:
            closes = d["Close"].dropna()
            if len(closes) >= 2:
                current = closes.iloc[-1]
                perf["1D"] = ((current / closes.iloc[-2]) - 1) * 100
                if len(closes) >= 6: perf["5D"] = ((current / closes.iloc[-6]) - 1) * 100
                if len(closes) >= 22: perf["1M"] = ((current / closes.iloc[-22]) - 1) * 100
                if len(closes) >= 250: perf["1Y"] = ((current / closes.iloc[0]) - 1) * 100
                
                # RSI 14
                if len(closes) >= 15:
                    delta = closes.diff()
                    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                    rs = gain / loss
                    rsi = 100 - (100 / (1 + rs))
                    perf["RSI"] = rsi.iloc[-1]
                
                # Reemplazar precio cacheado por precio fresco
                out["price"] = current
        
        out["perf"] = perf
        
        if row:
            out.update({
                "name": row.get("name"),
                "currency": row.get("currency"),
                "sector": row.get("sector"),
                "pe": row.get("pe"),
                "forwardPe": row.get("forwardPe"),
                "marketCap": row.get("marketCap"),
                "peMedian": row.get("peMedian"),
                "mos": row.get("mos"),
                "fairValue": row.get("fairValue"),
                "verdict": row.get("verdict"),
                "targetPessimistic": row.get("targetPessimistic"),
                "targetBase": row.get("targetBase"),
                "targetOpt": row.get("targetOpt"),
                "cagrBase": row.get("cagrBase"),
            })
            if "price" not in out or out["price"] is None:
                out["price"] = row.get("price")
                
            mos = row.get("mos")
            out["inBuyZone"] = (mos is not None and mos >= item.get("targetMos", 25))
        else:
            out["inBuyZone"] = None
            
        # Limpiar floats para JSON
        import math
        for k, v in out.items():
            if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                out[k] = None
        if "perf" in out:
            for k, v in out["perf"].items():
                if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                    out["perf"][k] = None
                    
        return out

    with ThreadPoolExecutor(max_workers=5) as ex:
        evaluated = list(ex.map(evaluate, items))
    return {"items": evaluated}


def add_symbol(symbol: str, target_mos: float = 25.0):
    symbol = symbol.upper().strip()
    items = _load()
    for it in items:
        if it["symbol"] == symbol:
            it["targetMos"] = target_mos
            _save(items)
            return items
    items.append({"symbol": symbol, "targetMos": target_mos,
                  "addedAt": int(time.time() * 1000)})
    _save(items)
    return items


def remove_symbol(symbol: str):
    symbol = symbol.upper().strip()
    items = [it for it in _load() if it["symbol"] != symbol]
    _save(items)
    return items


def has_symbol(symbol: str) -> bool:
    return any(it["symbol"] == symbol.upper().strip() for it in _load())
