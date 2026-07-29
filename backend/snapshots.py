"""Historial de margen de seguridad: una foto por símbolo y día (JSONL)."""

import json
from datetime import date
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
SNAP_FILE = DATA_DIR / "mos_history.jsonl"


def append(symbol: str, price, mos, fair):
    """Registra la foto del día. Se deduplica al leer (gana la última)."""
    if mos is None or price is None:
        return
    rec = {"d": date.today().isoformat(), "s": symbol.upper(),
           "p": round(float(price), 2), "m": round(float(mos), 1),
           "f": round(float(fair), 2) if fair is not None else None}
    with SNAP_FILE.open("a") as f:
        f.write(json.dumps(rec) + "\n")


def history(symbol: str):
    """[[ts_ms, mos, price, fair], ...] deduplicado por día (última foto gana)."""
    if not SNAP_FILE.exists():
        return []
    sym = symbol.upper()
    by_day = {}
    with SNAP_FILE.open() as f:
        for line in f:
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if rec.get("s") == sym:
                by_day[rec["d"]] = rec
    out = []
    for d in sorted(by_day):
        rec = by_day[d]
        ts = int(__import__("pandas").Timestamp(d).timestamp() * 1000)
        out.append([ts, rec["m"], rec["p"], rec.get("f")])
    return out
