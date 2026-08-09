"""El Inversor Inteligente — servidor FastAPI (API + frontend estático)."""

import os
from pathlib import Path

# Cargar variables de entorno desde .env
_env_file = Path(__file__).resolve().parent.parent / ".env"
if _env_file.exists():
    for line in _env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip("'\""))

import re
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, field_validator, Field


from . import notes as NT
from . import portfolio as PF
from . import watchlist as WL
from .data import atomic_write_json, clean_expired_cache
from .market import get_indices, get_movers, get_oversold
from .screener import run_deep_screener, run_screener
from .stock import build_payload
from .config import API_KEY, CACHE_VERSION


# ─── Auth simple para endpoints mutantes ───


def verify_api_key(x_api_key: str = Header(default=None, alias="X-API-Key")):
    if x_api_key != API_KEY:
        raise HTTPException(401, "API key inválida o faltante")
    return True


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        clean_expired_cache()
    except Exception:
        pass
    yield


app = FastAPI(title="El Inversor Inteligente", lifespan=lifespan)

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"


@app.middleware("http")
async def no_store_api(request, call_next):
    """Evita la caché heurística del navegador sobre los payloads de la API:
    sin esta cabecera Chrome cachea los JSON y la app muestra datos viejos
    hasta un refresco manual. Los estáticos ya se sirven con no-cache."""
    if request.url.path.startswith("/api/"):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        return response
    return await call_next(request)

_SYMBOL_RE = re.compile(r"^[A-Z0-9\.\-\/]{1,15}$")


def _clean_symbol(symbol: str) -> str:
    """Valida y normaliza un símbolo: quita espacios, mayúsculas, límite de longitud."""
    s = (symbol or "").strip().upper()
    if not _SYMBOL_RE.match(s):
        raise HTTPException(400, f"Símbolo inválido: '{symbol}'")
    return s


@app.get("/api/stock/{symbol}")
def api_stock(symbol: str, refresh: bool = False):
    sym = _clean_symbol(symbol)
    payload = build_payload(sym, refresh=refresh)
    if payload is None:
        raise HTTPException(404, f"No se encontraron datos para '{sym}'. Revisa el símbolo (ej: NVDA, AAPL, KO).")
    payload["inWatchlist"] = WL.has_symbol(sym)
    return payload


@app.get("/api/search")
def api_search(q: str):
    try:
        import yfinance as yf
        res = yf.Search(q, max_results=8)
        out = []
        for it in (res.quotes or []):
            if it.get("symbol") and it.get("quoteType") in ("EQUITY", "ETF"):
                out.append({
                    "symbol": it["symbol"],
                    "name": it.get("shortname") or it.get("longname") or "",
                    "exchange": it.get("exchDisp") or it.get("exchange") or "",
                })
        return {"results": out}
    except Exception:
        return {"results": []}


@app.get("/api/screener")
def api_screener(universe: str = "us", refresh: bool = False):
    return run_screener(universe=universe, refresh=refresh)


@app.get("/api/screener/deep")
def api_screener_deep(universe: str = "us", refresh: bool = False):
    return run_deep_screener(universe=universe, refresh=refresh)


@app.get("/api/quotes")
def api_quotes(symbols: str):
    """Cotizaciones en lote con sparkline de 30 días (sidebar de favoritos)."""
    import pandas as pd
    import yfinance as yf

    from .data import cache_get, cache_set

    syms = []
    for s in symbols.split(","):
        s = s.strip().upper()
        if not s:
            continue
        if not _SYMBOL_RE.match(s):
            raise HTTPException(400, f"Símbolo inválido: '{s}'")
        syms.append(s)
    syms = syms[:25]
    if not syms:
        return {"quotes": []}
    key = f"quotes_{CACHE_VERSION}_" + "_".join(sorted(syms)).replace("/", "_").replace(".", "_")
    cached = cache_get(key)
    if cached:
        return cached

    try:
        df = yf.download(syms, period="1mo", interval="1d", progress=False,
                         auto_adjust=True)["Close"]
        if isinstance(df, pd.Series):
            df = df.to_frame(name=syms[0])
        out = []
        for s in syms:
            if s not in df.columns:
                continue
            closes = df[s].dropna()
            if len(closes) < 2:
                continue
            out.append({
                "symbol": s,
                "price": round(float(closes.iloc[-1]), 2),
                "changePct": round((float(closes.iloc[-1]) / float(closes.iloc[-2]) - 1) * 100, 2),
                "spark": [round(float(v), 3) for v in closes.tolist()],
            })
        payload = {"quotes": out}
        cache_set(key, payload, ttl=600)
        return payload
    except Exception:
        return {"quotes": []}


class WatchItem(BaseModel):
    symbol: str
    targetMos: float = Field(25.0, ge=0, le=95)

    @field_validator("symbol")
    @classmethod
    def check_symbol(cls, v: str) -> str:
        s = v.strip().upper()
        if not s or len(s) > 15 or not re.match(r"^[A-Z0-9\.\-\/]+$", s):
            raise ValueError("Símbolo inválido")
        return s

    @field_validator("targetMos")
    @classmethod
    def check_target_mos(cls, v: float) -> float:
        return round(v, 2)


@app.get("/api/watchlist")
def api_watchlist():
    return WL.get_watchlist()


@app.post("/api/watchlist", dependencies=[Depends(verify_api_key)])
def api_watchlist_add(item: WatchItem):
    WL.add_symbol(item.symbol, item.targetMos)
    return {"ok": True}


@app.delete("/api/watchlist/{symbol}", dependencies=[Depends(verify_api_key)])
def api_watchlist_remove(symbol: str):
    WL.remove_symbol(_clean_symbol(symbol))
    return {"ok": True}


@app.get("/api/watchlist/symbols")
def api_watchlist_symbols():
    """Solo los símbolos (sin evaluación pesada) — para el sidebar."""
    return {"symbols": [it["symbol"] for it in WL._load()]}


class Position(BaseModel):
    symbol: str
    date: str
    price: float = Field(..., gt=0, le=1_000_000_000)
    shares: float = Field(..., gt=0, le=1_000_000_000)
    note: str = ""

    @field_validator("symbol")
    @classmethod
    def check_symbol(cls, v: str) -> str:
        s = v.strip().upper()
        if not s or len(s) > 15 or not re.match(r"^[A-Z0-9\.\-\/]+$", s):
            raise ValueError("Símbolo inválido")
        return s

    @field_validator("date")
    @classmethod
    def check_date(cls, v: str) -> str:
        s = v.strip()
        try:
            d = datetime.strptime(s, "%Y-%m-%d")
            if d > datetime.now() + timedelta(days=1):
                raise ValueError("La fecha no puede ser en el futuro")
            if d.year < 1970:
                raise ValueError("La fecha es demasiado antigua")
        except ValueError as e:
            raise ValueError(f"Fecha inválida (usar AAAA-MM-DD): {e}")
        return s

    @field_validator("price", "shares")
    @classmethod
    def round_values(cls, v: float) -> float:
        return round(v, 4)

    @field_validator("note")
    @classmethod
    def check_note(cls, v: str) -> str:
        return (v or "").strip()[:500]


@app.get("/api/portfolio")
def api_portfolio():
    return PF.get_portfolio()


@app.post("/api/portfolio", dependencies=[Depends(verify_api_key)])
def api_portfolio_add(p: Position):
    PF.add_position(p.symbol, p.date, p.price, p.shares, p.note)
    return {"ok": True}


@app.delete("/api/portfolio/{pid}", dependencies=[Depends(verify_api_key)])
def api_portfolio_remove(pid: int):
    PF.remove_position(pid)
    return {"ok": True}


class Note(BaseModel):
    thesis: str = ""
    risks: str = ""
    moats: list[str] = []

    @field_validator("thesis", "risks")
    @classmethod
    def check_text(cls, v: str) -> str:
        return (v or "").strip()[:2000]

    @field_validator("moats")
    @classmethod
    def check_moats(cls, v: list[str]) -> list[str]:
        valid = {"marca", "costos", "red", "switching", "intangibles", "escala"}
        return [m for m in (v or []) if m in valid]


@app.get("/api/notes/{symbol}")
def api_notes_get(symbol: str):
    return NT.get_note(_clean_symbol(symbol))


@app.post("/api/notes/{symbol}", dependencies=[Depends(verify_api_key)])
def api_notes_set(symbol: str, n: Note):
    return NT.set_note(_clean_symbol(symbol), n.thesis, n.risks, n.moats)


@app.get("/api/backup")
def api_backup():
    """Respaldo de todos tus datos personales en un solo JSON."""
    return {
        "version": 1,
        "watchlist": WL._load(),
        "portfolio": PF._load(),
        "notes": NT._load(),
    }


class Backup(BaseModel):
    version: int = 1
    watchlist: list = []
    portfolio: list = []
    notes: dict = {}

    @field_validator("watchlist")
    @classmethod
    def check_watchlist(cls, v: list) -> list:
        out = []
        for item in v:
            if isinstance(item, dict) and "symbol" in item:
                sym = str(item["symbol"]).strip().upper()[:15]
                if not _SYMBOL_RE.match(sym):
                    continue
                try:
                    target = float(item.get("targetMos", 25.0))
                except (TypeError, ValueError):
                    target = 25.0
                out.append({
                    "symbol": sym,
                    "targetMos": max(0.0, min(95.0, target)),
                    "addedAt": int(item.get("addedAt", 0) or 0),
                })
        return out

    @field_validator("portfolio")
    @classmethod
    def check_portfolio(cls, v: list) -> list:
        out = []
        for item in v:
            if isinstance(item, dict) and "symbol" in item and "price" in item and "shares" in item:
                sym = str(item["symbol"]).strip().upper()[:15]
                if not _SYMBOL_RE.match(sym):
                    continue
                try:
                    price = float(item["price"])
                    shares = float(item["shares"])
                except (TypeError, ValueError):
                    continue
                if not (0.0001 < price <= 1_000_000_000) or not (0.0001 < shares <= 1_000_000_000):
                    continue
                date = str(item.get("date", "2024-01-01"))
                try:
                    datetime.strptime(date, "%Y-%m-%d")
                except ValueError:
                    date = "2024-01-01"
                out.append({
                    "id": int(item.get("id", 0) or 0),
                    "symbol": sym,
                    "date": date,
                    "price": price,
                    "shares": shares,
                    "note": str(item.get("note", ""))[:300],
                })
        return out


@app.post("/api/restore", dependencies=[Depends(verify_api_key)])
def api_restore(b: Backup):
    # Validar notas antes de tocar disco (estructura estricta de dict[str, dict])
    notes = {}
    for k, v in b.notes.items():
        k = str(k).strip().upper()[:15]
        if not _SYMBOL_RE.match(k):
            continue
        if not isinstance(v, dict):
            continue
        notes[k] = {
            "thesis": str(v.get("thesis", ""))[:2000],
            "risks": str(v.get("risks", ""))[:2000],
            "moats": [str(m)[:30] for m in v.get("moats", []) if isinstance(m, (str, int))][:10],
        }
    # Escritura transaccional: validar ambos guardados antes de escribir notas
    WL._save(b.watchlist)
    PF._save(b.portfolio)
    atomic_write_json(NT.NOTES_FILE, notes)
    return {"ok": True}


@app.get("/api/dashboard/indices")
def api_dashboard_indices():
    return get_indices()


@app.get("/api/dashboard/oversold")
def api_dashboard_oversold():
    return get_oversold()


@app.get("/api/dashboard/movers")
def api_dashboard_movers():
    return get_movers()


class NoCacheStaticFiles(StaticFiles):
    def is_not_modified(self, response_headers, request_headers) -> bool:
        return False

    async def get_response(self, path, scope):
        # Strip conditional headers from request scope so StaticFiles never returns 304
        headers = [(k, v) for k, v in scope.get("headers", [])
                   if k.lower() not in (b"if-none-match", b"if-modified-since")]
        scope_copy = dict(scope, headers=headers)

        response = await super().get_response(path, scope_copy)
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        if "etag" in response.headers:
            del response.headers["etag"]
        if "last-modified" in response.headers:
            del response.headers["last-modified"]
        return response

app.mount("/", NoCacheStaticFiles(directory=str(FRONTEND), html=True), name="static")