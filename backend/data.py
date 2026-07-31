"""Capa de datos: descarga desde Yahoo Finance (yfinance) con caché en disco."""

import json
import math
import time
from pathlib import Path

import pandas as pd
import yfinance as yf

CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)

TTL_STOCK = 6 * 3600      # fundamentales: 6 horas
TTL_SCREENER = 24 * 3600  # screener: 24 horas


import os
import tempfile
import threading

_file_lock = threading.Lock()


def atomic_write_json(file_path: Path, data):
    """Escribe data a file_path de forma atómica y thread-safe mediante un archivo temporal y os.replace."""
    file_path = Path(file_path).resolve()
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with _file_lock:
        temp_fd, temp_name = tempfile.mkstemp(dir=file_path.parent, prefix=".tmp_", suffix=".json")
        try:
            with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_name, file_path)
        except Exception:
            if os.path.exists(temp_name):
                try:
                    os.remove(temp_name)
                except Exception:
                    pass
            raise


def load_json(file_path: Path, default=None):
    """Carga JSON de forma segura. Si el archivo está corrupto, lo respalda a
    `<nombre>.corrupt` (evitando que el siguiente write sobreescriba datos
    irrecuperables) y devuelve `default`."""
    file_path = Path(file_path)
    if not file_path.exists():
        return default
    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
        return data
    except Exception:
        try:
            bak = file_path.with_suffix(file_path.suffix + ".corrupt")
            bak.write_text(file_path.read_text(encoding="utf-8"), encoding="utf-8")
        except Exception:
            pass
        return default


def cache_get(key: str):
    f = CACHE_DIR / f"{key}.json"
    if not f.exists():
        return None
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
        if time.time() - data["_ts"] < data["_ttl"]:
            return data["payload"]
    except Exception:
        pass
    return None


def cache_set(key: str, payload, ttl: int = TTL_STOCK):
    f = CACHE_DIR / f"{key}.json"
    atomic_write_json(f, {"_ts": time.time(), "_ttl": ttl, "payload": payload})


def clean_expired_cache() -> int:
    """Elimina archivos JSON expirados del directorio de caché. Retorna la cantidad eliminada."""
    removed = 0
    now = time.time()
    for f in CACHE_DIR.glob("*.json"):
        try:
            data = json.loads(f.read_text())
            ts, ttl = data.get("_ts", 0), data.get("_ttl", 0)
            # ttl=0 son marcadores de invalidación: se pueden borrar de inmediato.
            # ttl<0 (inexistente) y archivos con más de 30 días: se purgan.
            if ttl == 0 or (ttl > 0 and now - ts >= ttl) or (now - ts >= 30 * 86400):
                f.unlink(missing_ok=True)
                removed += 1
        except Exception:
            continue
    return removed


def jclean(obj):
    """Convierte tipos numpy/pandas y NaN/inf a JSON válido."""
    if isinstance(obj, dict):
        return {str(k): jclean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [jclean(v) for v in obj]
    if isinstance(obj, (pd.Timestamp,)):
        return int(obj.timestamp() * 1000)
    if hasattr(obj, "item"):  # numpy scalar
        obj = obj.item()
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    return obj


class RawData:
    """Descarga todo lo necesario de Yahoo para un símbolo, en paralelo."""

    def __init__(self, symbol: str):
        from concurrent.futures import ThreadPoolExecutor

        self.symbol = symbol
        start = (pd.Timestamp.now() - pd.DateOffset(years=10)).strftime("%Y-%m-%d")

        # cada tarea usa su propio Ticker: yfinance no garantiza thread-safety
        # sobre la misma instancia
        def T():
            return yf.Ticker(symbol)

        tasks = {
            "info": lambda: T().info or {},
            "prices": lambda: T().history(period="max", interval="1d", auto_adjust=True),
            "inc_a": lambda: T().income_stmt,
            "inc_q": lambda: T().quarterly_income_stmt,
            "bs_a": lambda: T().balance_sheet,
            "bs_q": lambda: T().quarterly_balance_sheet,
            "cf_a": lambda: T().cashflow,
            "cf_q": lambda: T().quarterly_cashflow,
            "dividends": lambda: T().dividends,
            "calendar": lambda: T().calendar,
            "shares": lambda: T().get_shares_full(start=start),
            "recommendations": lambda: T().recommendations,
            "earnings_estimate": lambda: T().earnings_estimate,
            "revenue_estimate": lambda: T().revenue_estimate,
            "earnings_dates": lambda: T().earnings_dates,
            "insider_transactions": lambda: T().insider_transactions,
            "institutional_holders": lambda: T().institutional_holders,
            "news": lambda: T().news,
        }
        with ThreadPoolExecutor(max_workers=8) as ex:
            futures = {name: ex.submit(self._safe, fn) for name, fn in tasks.items()}
            results = {}
            for name, fut in futures.items():
                try:
                    results[name] = fut.result(timeout=45)
                except Exception:
                    results[name] = None

        self.info = results["info"] or {}
        self.prices = results["prices"]
        if self.prices is not None and not self.prices.empty:
            self.prices.index = self.prices.index.tz_localize(None)

        self.inc_a, self.inc_q = results["inc_a"], results["inc_q"]
        self.bs_a, self.bs_q = results["bs_a"], results["bs_q"]
        self.cf_a, self.cf_q = results["cf_a"], results["cf_q"]

        self.dividends = results["dividends"]
        if self.dividends is not None and not self.dividends.empty:
            self.dividends.index = self.dividends.index.tz_localize(None)

        self.calendar = results["calendar"] or {}

        self.shares = results["shares"]
        if self.shares is not None and not self.shares.empty:
            self.shares.index = self.shares.index.tz_localize(None)
            self.shares = self.shares[~self.shares.index.duplicated(keep="last")]

        self.recommendations = results["recommendations"]
        self.earnings_estimate = results["earnings_estimate"]
        self.revenue_estimate = results["revenue_estimate"]
        self.earnings_dates = results["earnings_dates"]
        self.insider_transactions = results["insider_transactions"]
        self.institutional_holders = results["institutional_holders"]
        self.news = results["news"]

    @staticmethod
    def _safe(fn):
        try:
            out = fn()
            if out is None:
                return None
            if hasattr(out, "empty") and out.empty:
                return None
            return out
        except Exception:
            return None

    def is_valid(self) -> bool:
        return self.prices is not None and not self.prices.empty


def bond_yield_10y() -> float:
    """Rendimiento del bono del Tesoro EE.UU. a 10 años (en %), con caché."""
    cached = cache_get("_bond10y")
    if cached is not None:
        return cached
    try:
        h = yf.Ticker("^TNX").history(period="5d")
        y = float(h["Close"].dropna().iloc[-1])
        cache_set("_bond10y", y, ttl=12 * 3600)
        return y
    except Exception:
        return 4.3  # valor razonable de respaldo
