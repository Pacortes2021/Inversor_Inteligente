"""El Inversor Inteligente — servidor FastAPI (API + frontend estático)."""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import notes as NT
from . import portfolio as PF
from . import watchlist as WL
from .screener import run_deep_screener, run_screener
from .stock import build_payload

app = FastAPI(title="El Inversor Inteligente")

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"


@app.get("/api/stock/{symbol}")
def api_stock(symbol: str, refresh: bool = False):
    payload = build_payload(symbol.strip(), refresh=refresh)
    if payload is None:
        raise HTTPException(404, f"No se encontraron datos para '{symbol}'. Revisa el símbolo (ej: NVDA, AAPL, KO).")
    payload["inWatchlist"] = WL.has_symbol(symbol)
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

    syms = [s.strip().upper() for s in symbols.split(",") if s.strip()][:25]
    if not syms:
        return {"quotes": []}
    key = "quotes_" + "_".join(sorted(syms)).replace("/", "_").replace(".", "_")
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
    targetMos: float = 25.0


@app.get("/api/watchlist")
def api_watchlist():
    return WL.get_watchlist()


@app.post("/api/watchlist")
def api_watchlist_add(item: WatchItem):
    WL.add_symbol(item.symbol, item.targetMos)
    return {"ok": True}


@app.delete("/api/watchlist/{symbol}")
def api_watchlist_remove(symbol: str):
    WL.remove_symbol(symbol)
    return {"ok": True}


@app.get("/api/watchlist/symbols")
def api_watchlist_symbols():
    """Solo los símbolos (sin evaluación pesada) — para el sidebar."""
    return {"symbols": [it["symbol"] for it in WL._load()]}


class Position(BaseModel):
    symbol: str
    date: str
    price: float
    shares: float
    note: str = ""


@app.get("/api/portfolio")
def api_portfolio():
    return PF.get_portfolio()


@app.post("/api/portfolio")
def api_portfolio_add(p: Position):
    PF.add_position(p.symbol, p.date, p.price, p.shares, p.note)
    return {"ok": True}


@app.delete("/api/portfolio/{pid}")
def api_portfolio_remove(pid: int):
    PF.remove_position(pid)
    return {"ok": True}


class Note(BaseModel):
    thesis: str = ""
    risks: str = ""
    moats: list[str] = []


@app.get("/api/notes/{symbol}")
def api_notes_get(symbol: str):
    return NT.get_note(symbol)


@app.post("/api/notes/{symbol}")
def api_notes_set(symbol: str, n: Note):
    return NT.set_note(symbol, n.thesis, n.risks, n.moats)


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


@app.post("/api/restore")
def api_restore(b: Backup):
    WL._save(b.watchlist)
    PF._save(b.portfolio)
    import json
    NT.NOTES_FILE.write_text(json.dumps(b.notes, indent=2, ensure_ascii=False))
    return {"ok": True}


app.mount("/", StaticFiles(directory=str(FRONTEND), html=True), name="static")
