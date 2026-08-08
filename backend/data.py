"""Capa de datos: descarga desde Yahoo Finance (yfinance) con caché en disco."""

import json
import math
import time
from pathlib import Path

import pandas as pd

from .yfinance_wrapper import (
    safe_ticker, safe_info, safe_history, safe_financials, safe_dividends,
    safe_calendar, safe_shares, safe_recommendations, safe_earnings_estimate,
    safe_revenue_estimate, safe_earnings_dates, safe_insider_transactions,
    safe_institutional_holders, safe_news, safe_download, is_degraded,
)

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
    """Descarga datos para un símbolo utilizando el proveedor configurado (FMP o yfinance fallback)."""

    def __init__(self, symbol: str):
        from .providers.factory import fetch_data_with_fallback

        self.symbol = symbol
        data = fetch_data_with_fallback(symbol)

        self.provider = data.get("provider", "unknown")
        self.info = data.get("info") or {}
        self.prices = data.get("prices")
        self.inc_a = data.get("inc_a")
        self.inc_q = data.get("inc_q")
        self.bs_a = data.get("bs_a")
        self.bs_q = data.get("bs_q")
        self.cf_a = data.get("cf_a")
        self.cf_q = data.get("cf_q")
        self.dividends = data.get("dividends")
        self.calendar = data.get("calendar") or {}
        self.shares = data.get("shares")
        self.recommendations = data.get("recommendations")
        self.earnings_estimate = data.get("earnings_estimate")
        self.revenue_estimate = data.get("revenue_estimate")
        self.earnings_dates = data.get("earnings_dates")
        self.insider_transactions = data.get("insider_transactions")
        self.institutional_holders = data.get("institutional_holders")
        self.news = data.get("news")

    def is_valid(self) -> bool:
        return self.prices is not None and not self.prices.empty



def nasdaq_history(symbol, start, end, interval="1d"):
    """Histórico EOD de Nasdaq (ajustado por splits) como fallback de Yahoo.

    Devuelve un DataFrame con Open/High/Low/Close/Volume (índice de fechas
    tz-naive) o None. `interval="1mo"` resamplea el cierre mensual.
    """
    from .config import CACHE_VERSION

    key = f"nq_{CACHE_VERSION}_{symbol.replace('/', '_').replace('.', '_')}_{start}_{end}"
    cached = cache_get(key)
    if cached:
        rows = cached
    else:
        rows = None
        try:
            import requests

            url = "https://api.nasdaq.com/api/quote/{}/historical".format(symbol)
            r = requests.get(
                url,
                params={
                    "assetclass": "stocks",
                    "fromdate": start,
                    "todate": end,
                    "limit": 99999,
                },
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
                    "Accept": "application/json",
                    "Referer": "https://www.nasdaq.com/",
                },
                timeout=20,
            )
            if r.status_code == 200:
                data = r.json()
                table = ((data.get("data") or {}).get("tradesTable") or {})
                rows = table.get("rows") or None
        except Exception:
            rows = None
        if rows:
            cache_set(key, rows, ttl=6 * 3600)

    if not rows:
        return None
    out = []
    for r in rows:
        try:
            d = pd.to_datetime(r.get("date"))
            close = float((r.get("close") or "").replace("$", "").replace(",", ""))
            o = float((r.get("open") or "").replace("$", "").replace(",", "")) or close
            h = float((r.get("high") or "").replace("$", "").replace(",", "")) or close
            l = float((r.get("low") or "").replace("$", "").replace(",", "")) or close
            v = int((r.get("volume") or "0").replace(",", "")) or 0
            out.append((d, o, h, l, close, v))
        except Exception:
            continue
    if not out:
        return None
    df = pd.DataFrame(out, columns=["Date", "Open", "High", "Low", "Close", "Volume"])
    df = df.set_index("Date").sort_index()
    if interval == "1mo":
        monthly = df["Close"].resample("ME").last().dropna()
        df = pd.DataFrame({"Open": monthly, "High": monthly, "Low": monthly, "Close": monthly, "Volume": 0})
    return df


def price_history(symbol, period=None, start=None, end=None, interval="1d"):
    """Serie de precios ajustada: Yahoo primero, fallback Nasdaq (US)."""
    try:
        if period:
            h = safe_download(symbol, period=period, interval=interval, progress=False, auto_adjust=True)
        else:
            h = safe_download(symbol, start=start, end=end, interval=interval, progress=False, auto_adjust=True)
        if h is not None and not h.empty:
            return h
    except Exception:
        pass
    if not start:
        days = {"1mo": 30, "3mo": 90, "6mo": 180, "1y": 365, "5y": 1825, "10y": 3650, "12y": 4380, "15y": 5480}.get(period, 365)
        start = (pd.Timestamp.now() - pd.DateOffset(days=days)).strftime("%Y-%m-%d")
    end = end or pd.Timestamp.now().strftime("%Y-%m-%d")
    h = nasdaq_history(symbol, start, end, interval=interval)
    if h is not None:
        return h
    return None


def bond_yield_10y() -> float:
    """Rendimiento del bono del Tesoro EE.UU. a 10 años (en %), con caché.

    Fuente primaria: FRED (DGS10, CSV sin API key). Fallback: ^TNX vía Yahoo.
    """
    cached = cache_get("_bond10y_v4")
    if cached is not None:
        return cached
    try:
        df = pd.read_csv("https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10")
        if df is not None and len(df) >= 1:
            col = df.columns[-1]
            y = float(pd.to_numeric(df[col], errors="coerce").dropna().iloc[-1])
            if y > 0:
                cache_set("_bond10y_v4", round(y, 2), ttl=12 * 3600)
                return round(y, 2)
    except Exception:
        pass
    try:
        h = safe_download("^TNX", period="5d", interval="1d", progress=False, auto_adjust=True)
        if h is not None and not h.empty:
            y = float(h["Close"].dropna().iloc[-1])
            cache_set("_bond10y_v4", y, ttl=12 * 3600)
            return y
    except Exception:
        pass
    return 4.3  # valor razonable de respaldo