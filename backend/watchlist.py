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
    """Lista con evaluación actual: precio, MoS y si está en zona de compra."""
    items = _load()
    if not items:
        return {"items": []}
    bond10y = bond_yield_10y()

    def evaluate(item):
        row = scan_one_deep(item["symbol"], bond10y)
        out = {**item}
        if row:
            out.update({
                "name": row.get("name"),
                "price": row.get("price"),
                "currency": row.get("currency"),
                "sector": row.get("sector"),
                "pe": row.get("pe"),
                "peMedian": row.get("peMedian"),
                "mos": row.get("mos"),
                "fairValue": row.get("fairValue"),
                "verdict": row.get("verdict"),
                "targetCons": row.get("targetCons"),
                "targetBase": row.get("targetBase"),
                "targetOpt": row.get("targetOpt"),
                "cagrBase": row.get("cagrBase"),
            })
            mos = row.get("mos")
            out["inBuyZone"] = (mos is not None and mos >= item.get("targetMos", 25))
        else:
            out["inBuyZone"] = None
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
