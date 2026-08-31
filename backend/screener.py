"""Screener de valor con dos modos:

- rápido: métricas actuales de Yahoo (1 llamada por acción)
- profundo: valoración completa (DCF + reversión al PE mediano de 15 años vía
  EDGAR + Graham) → margen de seguridad por acción. Corre en un hilo de fondo
  con progreso consultable.
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import yfinance as yf

from . import edgar as E
from . import metrics as M
from . import valuation as V
from .data import TTL_SCREENER, bond_yield_10y, cache_get, cache_set, jclean, price_history
from .config import CACHE_VERSION

# ------------------------------------------------------------------ universos

UNIVERSE_US = [
    # mega caps / tecnología
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AVGO", "ORCL",
    "ADBE", "CRM", "CSCO", "ACN", "INTU", "IBM", "QCOM", "TXN", "AMD", "INTC",
    "AMAT", "MU", "LRCX", "KLAC", "ADI", "NXPI", "MRVL", "MCHP", "ANET", "NOW",
    "PANW", "CRWD", "FTNT", "SNPS", "CDNS", "ADSK", "WDAY", "SNOW", "DDOG",
    "TEAM", "SHOP", "UBER", "ABNB", "DASH", "PYPL", "COIN", "EBAY", "TTD",
    "EA", "TTWO", "RBLX", "MTCH", "PINS", "SPOT", "NFLX", "DIS", "CMCSA",
    "TMUS", "VZ", "T", "HPQ", "DELL",
    # financieras
    "BRK-B", "JPM", "V", "MA", "BAC", "WFC", "C", "GS", "MS", "SCHW", "BLK",
    "AXP", "USB", "PNC", "COF", "BK", "CB", "PGR", "MET", "AIG", "TRV", "ALL",
    "KKR", "BX", "CME", "ICE", "SPGI", "MCO", "MSCI", "NDAQ",
    # salud
    "LLY", "UNH", "JNJ", "ABBV", "MRK", "PFE", "TMO", "ABT", "DHR", "AMGN",
    "GILD", "ISRG", "SYK", "BSX", "MDT", "EW", "BDX", "REGN", "VRTX", "BIIB",
    "ZTS", "MCK", "CI", "ELV", "HUM", "HCA", "CVS",
    # consumo
    "WMT", "PG", "KO", "PEP", "COST", "HD", "LOW", "MCD", "SBUX", "NKE",
    "TGT", "TJX", "ROST", "DG", "DLTR", "KR", "EL", "CL", "KMB", "GIS", "K",
    "HSY", "SYY", "MO", "PM", "KHC", "MDLZ", "STZ", "YUM", "CMG", "DPZ",
    "MAR", "HLT", "RCL", "BKNG", "F", "GM",
    # industriales
    "CAT", "DE", "HON", "GE", "MMM", "EMR", "ETN", "ITW", "PH", "CMI", "PCAR",
    "BA", "LMT", "RTX", "GD", "NOC", "LHX", "TDG", "UNP", "CSX", "NSC", "FDX",
    "UPS", "DAL", "UAL", "LUV", "ADP", "WM", "RSG",
    # energía y materiales
    "XOM", "CVX", "COP", "EOG", "SLB", "HAL", "OXY", "PSX", "VLO", "MPC",
    "KMI", "WMB", "FCX", "NEM", "NUE", "DOW", "DD", "APD", "SHW", "ECL", "LIN",
    # utilities y REITs
    "NEE", "DUK", "SO", "D", "AEP", "EXC", "SRE", "PLD", "AMT", "CCI", "EQIX",
    "SPG", "O", "PSA",
]

UNIVERSE_CL = [
    # IPSA (índice selectivo)
    "SQM-B.SN", "COPEC.SN", "CENCOSUD.SN", "FALABELLA.SN", "BSANTANDER.SN",
    "CHILE.SN", "BCI.SN", "ENELCHILE.SN", "ENELAM.SN", "COLBUN.SN", "CCU.SN",
    "ANDINA-B.SN", "CMPC.SN", "VAPORES.SN", "LTM.SN", "PARAUCO.SN",
    "RIPLEY.SN", "SMU.SN", "AGUAS-A.SN", "CAP.SN", "ENTEL.SN", "SONDA.SN",
    "QUINENCO.SN", "CONCHATORO.SN", "IAM.SN", "ECL.SN", "SECURITY.SN",
    "MALLPLAZA.SN", "CENCOSHOPP.SN", "ITAUCL.SN",
    # holdings e inversiones
    "ANTARCHILE.SN", "ILC.SN", "PAZ.SN",
    # industriales y construcción
    "SK.SN", "BESALCO.SN", "SALFACORP.SN", "CGE.SN", "POLPAICO.SN", "MELON.SN",
    # minería y materiales
    "MOLYMET.SN", "ENAEX.SN", "MASISA.SN",
    # consumo y retail
    "GASCO.SN", "FORUS.SN", "HITES.SN", "EMBONOR-B.SN", "ANDINA-A.SN",
    "SQM-A.SN", "VSPT.SN", "IANSA.SN", "CRISTALES.SN", "BLUMAR.SN",
]

UNIVERSES = {"us": UNIVERSE_US, "cl": UNIVERSE_CL}


def _retry(fn, tries=3, wait=1.5):
    """Reintenta ante errores transitorios (rate limit de Yahoo, red)."""
    last = None
    for i in range(tries):
        try:
            return fn()
        except Exception as e:
            last = e
            time.sleep(wait * (i + 1))
    raise last


def _sma_last(values, n):
    """SMA de los últimos n valores; None si faltan datos."""
    if not values:
        return None
    values = [v for v in values if v is not None and v == v]  # descarta NaN
    if len(values) < n:
        return None
    return round(sum(values[-n:]) / n, 2)


def _fetch_sma_batch(symbols):
    """SMA200 diaria (1 año) y semanal (5 años) para un lote de símbolos en una
    sola descarga de Yahoo por intervalo. Devuelve {symbol: {...}}."""
    out = {}
    syms = [s for s in symbols if s]
    if not syms:
        return out

    daily = None
    try:
        daily = yf.download(syms, period="1y", interval="1d", progress=False,
                            auto_adjust=True, threads=False)
    except Exception:
        pass
    weekly = None
    try:
        weekly = yf.download(syms, period="5y", interval="1wk", progress=False,
                             auto_adjust=True, threads=False)
    except Exception:
        pass

    def _close_series(df, symbol):
        if df is None or df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            if symbol not in df.columns.get_level_values(1):
                return None
            s = df["Close"][symbol]
        else:
            if "Close" not in df.columns:
                return None
            s = df["Close"]
        s = pd.Series(s).dropna()
        return s if len(s) >= 50 else None

    for symbol in syms:
        d = _close_series(daily, symbol)
        w = _close_series(weekly, symbol)
        sma200d = _sma_last(list(d), 200) if d is not None else None
        sma200w = _sma_last(list(w), 200) if w is not None else None
        if sma200d is None and sma200w is None:
            continue
        last_idx = None
        if d is not None:
            last_idx = d.index[-1]
        elif w is not None:
            last_idx = w.index[-1]
        entry = {}
        if sma200d is not None:
            entry["sma200d"] = sma200d
        if sma200w is not None:
            entry["sma200w"] = sma200w
        if last_idx is not None:
            entry["date"] = pd.Timestamp(last_idx).strftime("%Y-%m-%d")
        out[symbol] = entry
    return out


def _inject_sma(results):
    """Añade a cada fila sma200d/sma200w y la distancia % del precio a cada SMA."""
    if not results:
        return
    sma_map = _fetch_sma_batch([r.get("symbol") for r in results])
    for r in results:
        entry = sma_map.get(r.get("symbol"))
        if not entry:
            continue
        r["sma200d"] = entry.get("sma200d")
        r["sma200w"] = entry.get("sma200w")
        r["smaDate"] = entry.get("date")
        price = r.get("price")
        if price and price > 0:
            if entry.get("sma200d"):
                r["distSma200d"] = round((price / entry["sma200d"] - 1) * 100, 2)
            if entry.get("sma200w"):
                r["distSma200w"] = round((price / entry["sma200w"] - 1) * 100, 2)


def _clip(x, lo, hi):
    return max(lo, min(hi, x))


def _scale(x, x0, x1):
    if x is None:
        return None
    if x1 == x0:
        return 50.0
    return _clip((x - x0) / (x1 - x0) * 100.0, 0.0, 100.0)


# ------------------------------------------------------------- modo rápido

def score_stock(info):
    price = info.get("currentPrice")
    pe = info.get("trailingPE")
    fpe = info.get("forwardPE")
    mc = info.get("marketCap")
    fcf = info.get("freeCashflow")
    roe = info.get("returnOnEquity")
    nm = info.get("profitMargins")
    de = info.get("debtToEquity")
    hi52 = info.get("fiftyTwoWeekHigh")

    ey = (1 / pe * 100) if pe and pe > 0 else None
    fey = (1 / fpe * 100) if fpe and fpe > 0 else None
    fcfy = (fcf / mc * 100) if (fcf and mc and fcf > 0) else None
    drawdown = (price / hi52 - 1) * 100 if (price and hi52) else None

    val_parts = [s for s in (_scale(ey, 1, 10), _scale(fey, 1, 10), _scale(fcfy, 0, 8)) if s is not None]
    quality_parts = [s for s in (_scale((roe or 0) * 100 if roe is not None else None, 0, 30),
                                 _scale((nm or 0) * 100 if nm is not None else None, 0, 25)) if s is not None]
    health = _scale(2 - (de / 100 if de is not None else 1.0), 0, 2)
    contrarian = _scale(abs(drawdown) if drawdown is not None else None, 0, 40)

    if not val_parts:
        return None
    score, weights = 0.0, 0.0
    score += (sum(val_parts) / len(val_parts)) * 0.45; weights += 0.45
    if quality_parts:
        score += (sum(quality_parts) / len(quality_parts)) * 0.30; weights += 0.30
    if health is not None:
        score += health * 0.15; weights += 0.15
    if contrarian is not None:
        score += contrarian * 0.10; weights += 0.10

    return {
        "score": round(score / weights, 1),
        "earningsYield": round(ey, 2) if ey else None,
        "fcfYield": round(fcfy, 2) if fcfy else None,
        "drawdown": round(drawdown, 1) if drawdown is not None else None,
    }


def _calc_target_scenarios(price, pe, fpe, pe_median, info, eps2030_override=None):
    if not price or price <= 0:
        return {}
    
    clean_pe = pe if (pe and 0 < pe <= 80 and (not fpe or pe <= 3 * fpe)) else None
    clean_fpe = fpe if (fpe and 0 < fpe <= 80) else None
    clean_med = pe_median if (pe_median and 0 < pe_median <= 80) else None

    # Base PE: usar la Mediana Histórica del PER (si existe y es razonable).
    # Si la mediana no está disponible o es atípica (>80x o >3x fwd PE), usar Forward PE (o trailing PE).
    raw_med = clean_med or clean_fpe or clean_pe or 20.0
    if clean_fpe and raw_med > 3 * clean_fpe:
        raw_med = clean_fpe
    base_pe = max(5.0, min(80.0, raw_med))

    cons_pe = max(5.0, base_pe * 0.80)
    opt_pe = base_pe * 1.20

    if eps2030_override is not None and eps2030_override > 0:
        eps_2030 = eps2030_override
    else:
        growth_est = info.get("earningsGrowth") or info.get("revenueGrowth") or 0.10
        if growth_est > 0.40: growth_est = 0.20
        if growth_est < -0.05: growth_est = 0.03
        
        eps_current = (price / clean_pe) if clean_pe else None
        eps_fwd = (price / clean_fpe) if clean_fpe else None
        
        eps_base = eps_fwd if eps_fwd else (eps_current if eps_current else (price / base_pe))
        if not eps_base or eps_base <= 0:
            return {}
            
        eps_2030 = round(eps_base * ((1 + growth_est) ** 4), 2)
    
    def _target_metrics(target_pe):
        target_p = round(eps_2030 * target_pe, 2)
        tot_ret = round(((target_p - price) / price) * 100.0, 1)
        cagr = round(((target_p / price) ** (1.0 / 4.0) - 1.0) * 100.0, 1) if (price > 0 and target_p > 0) else 0.0
        return target_p, tot_ret, cagr

    cons_p, cons_tot, cons_cagr = _target_metrics(cons_pe)
    base_p, base_tot, base_cagr = _target_metrics(base_pe)
    opt_p, opt_tot, opt_cagr = _target_metrics(opt_pe)
    
    return {
        "eps2030": eps_2030,
        "consPe": round(cons_pe, 1),
        "targetCons": cons_p,
        "targetPessimistic": cons_p,
        "retCons": cons_tot,
        "cagrCons": cons_cagr,
        "basePe": round(base_pe, 1),
        "targetBase": base_p,
        "retBase": base_tot,
        "cagrBase": base_cagr,
        "optPe": round(opt_pe, 1),
        "targetOpt": opt_p,
        "retOpt": opt_tot,
        "cagrOpt": opt_cagr,
    }


def _base_row(symbol, info):
    de = info.get("debtToEquity")
    price = info.get("currentPrice")
    pe = round(info["trailingPE"], 1) if info.get("trailingPE") else None
    fpe = round(info["forwardPE"], 1) if info.get("forwardPE") else None

    div_rate = info.get("dividendRate")
    div_yield_raw = info.get("dividendYield") or info.get("trailingAnnualDividendYield")

    div_yield_pct = None
    if div_rate and price and price > 0:
        div_yield_pct = round((float(div_rate) / float(price)) * 100, 2)
    elif div_yield_raw and div_yield_raw > 0:
        y_val = float(div_yield_raw)
        div_yield_pct = round(y_val * 100, 2) if y_val <= 1.0 else round(y_val, 2)

    if div_yield_pct is not None and div_yield_pct < 0.05:
        div_yield_pct = None

    edgar_hist = E.get_annual_history(symbol)
    pe_stats = _pe_stats_from_edgar(symbol, edgar_hist) if edgar_hist else None
    pe_med = pe_stats["median"] if pe_stats else None
    scenarios = _calc_target_scenarios(price, pe, fpe, pe_med, info)

    return {
        "symbol": symbol,
        "name": info.get("shortName") or symbol,
        "sector": info.get("sector"),
        "price": price,
        "currency": info.get("currency") or "USD",
        "marketCap": info.get("marketCap"),
        "pe": pe,
        "forwardPe": fpe,
        "divYield": div_yield_pct,
        "pb": round(info["priceToBook"], 2) if info.get("priceToBook") else None,
        "roe": round(info["returnOnEquity"] * 100, 1) if info.get("returnOnEquity") is not None else None,
        "netMargin": round(info["profitMargins"] * 100, 1) if info.get("profitMargins") is not None else None,
        "debtToEquity": round(de / 100, 2) if de is not None else None,
        **scenarios,
    }


def scan_one(symbol):
    try:
        info = _retry(lambda: yf.Ticker(symbol).info or {})
        s = score_stock(info)
        if not s:
            return None
        return {**_base_row(symbol, info), **s}
    except Exception:
        return None


def run_screener(universe: str = "us", refresh: bool = False):
    universe = universe if universe in UNIVERSES else "us"
    key = f"screener_{CACHE_VERSION}_{universe}"
    if not refresh:
        cached = cache_get(key)
        if cached:
            return cached

    results = []
    with ThreadPoolExecutor(max_workers=6) as ex:
        futures = {ex.submit(scan_one, s): s for s in UNIVERSES[universe]}
        for fut in as_completed(futures):
            r = fut.result()
            if r:
                results.append(r)

    results.sort(key=lambda r: r["score"], reverse=True)
    _inject_sma(results)
    payload = jclean({"count": len(results), "universe": universe,
                      "updatedAt": int(time.time() * 1000), "results": results})
    cache_set(key, payload, ttl=TTL_SCREENER)
    return payload


# ------------------------------------------------------------ modo profundo

_deep_lock = threading.Lock()
_deep_states = {}


def _pe_stats_from_edgar(symbol, edgar_hist):
    """Mediana histórica del PE con EPS anual de EDGAR (ajustado por splits)
    y precios mensuales ajustados de Yahoo."""
    eps = E.to_series(edgar_hist, "eps")
    if eps is None or len(eps) < 4:
        return None
    try:
        h = yf.Ticker(symbol).history(period="15y", interval="1mo")
        if h is None or h.empty:
            h = None
    except Exception:
        h = None
    if h is None:
        h = price_history(symbol, period="15y", interval="1mo")
    if h is None or h.empty:
        return None
    h.index = h.index.tz_localize(None) if getattr(h.index, "tz", None) is not None else h.index
    eps = M.split_adjust(eps, M.splits_from_prices(h), "per_share")
    monthly = h["Close"].dropna()
    pe = M.ratio_history(monthly, eps, "per_share")
    if pe is None:
        return None
    pe = pe[pe <= 200]  # PE de utilidad casi nula no es señal de valoración
    return M.series_stats(M._pairs(pe, 2))


def scan_one_deep(symbol, bond10y):
    cached = cache_get(f"deep_{CACHE_VERSION}_{symbol.replace('/', '_').replace('.', '_')}")
    if cached:
        return cached
    try:
        info = _retry(lambda: yf.Ticker(symbol).info or {})
        price = info.get("currentPrice")
        if not price:
            return None

        edgar_hist = E.get_annual_history(symbol)
        pe_stats = _pe_stats_from_edgar(symbol, edgar_hist) if edgar_hist else None
        annuals = E.to_annual_rows(edgar_hist) if edgar_hist else []

        val = V.build_valuation(price, info, annuals, pe_stats, bond10y)
        quick = score_stock(info) or {}

        # guardas de calidad: MoS extremos suelen ser datos malos, no gangas;
        # con un solo modelo el consenso no es confiable
        mos, fair, verdict = val["marginOfSafety"], val["consensus"], val["verdict"]
        if mos is not None and mos > 300:
            mos, fair = None, None
            verdict = {"label": "Datos poco confiables", "level": "na"}
        elif len(val["models"]) < 2:
            verdict = {"label": "Modelos insuficientes", "level": "na"}

        roc = V.greenblatt_roc(info, annuals)
        f_score = V.piotroski_f_score(annuals)
        
        from .estimates import build_estimates_payload
        raw = yf.Ticker(symbol)
        est = build_estimates_payload(raw, info, annuals, price, symbol=symbol)
        eps_2030 = None
        grid = est.get("growthGrid", {}) if est else {}
        if grid and "rows" in grid:
            for r in grid["rows"]:
                if r.get("label") == "EPS" and r.get("values"):
                    eps_val = r["values"][-1]
                    if eps_val is not None:
                        eps_2030 = float(eps_val)
                    break

        deep_scenarios = _calc_target_scenarios(price, info.get("trailingPE"), info.get("forwardPE"), pe_stats["median"] if pe_stats else None, info, eps2030_override=eps_2030)

        row = {
            **_base_row(symbol, info),
            **deep_scenarios,
            "fcfYield": quick.get("fcfYield"),
            "earningsYield": quick.get("earningsYield"),
            "drawdown": quick.get("drawdown"),
            "score": quick.get("score"),
            "peMedian": pe_stats["median"] if pe_stats else None,
            "vsMedian": pe_stats["vsMedian"] if pe_stats else None,
            "mos": mos,
            "verdict": verdict,
            "fairValue": fair,
            "nModels": len(val["models"]),
            "roc": round(roc, 1) if roc else None,
            "fScore": f_score,
        }
        row = jclean(row)
        cache_set(f"deep_{CACHE_VERSION}_{symbol.replace('/', '_').replace('.', '_')}", row, ttl=TTL_SCREENER)

        # alimenta el historial de margen de seguridad (cálculo fresco del día)
        from . import snapshots as S
        S.append(symbol, row.get("price"), row.get("mos"), row.get("fairValue"))
        return row
    except Exception:
        return None


def _deep_worker(universe):
    symbols = UNIVERSES[universe]
    bond10y = bond_yield_10y()
    results = []
    try:
        with ThreadPoolExecutor(max_workers=5) as ex:
            futures = {ex.submit(scan_one_deep, s, bond10y): s for s in symbols}
            for fut in as_completed(futures):
                r = fut.result()
                if r:
                    results.append(r)
                with _deep_lock:
                    if universe in _deep_states:
                        _deep_states[universe]["done"] += 1
        results.sort(key=lambda r: (r["mos"] is None, -(r["mos"] if r["mos"] is not None else -999)))
        _inject_sma(results)
        payload = jclean({"count": len(results), "universe": universe,
                          "updatedAt": int(time.time() * 1000), "results": results})
        cache_set(f"deep_screener_{CACHE_VERSION}_{universe}", payload, ttl=TTL_SCREENER)
        with _deep_lock:
            if universe in _deep_states:
                _deep_states[universe]["status"] = "done"
    except Exception:
        with _deep_lock:
            if universe in _deep_states:
                _deep_states[universe]["status"] = "error"


def run_deep_screener(universe: str = "us", refresh: bool = False):
    """Devuelve resultados cacheados, o el progreso del escaneo en curso para el universo dado."""
    universe = universe if universe in UNIVERSES else "us"

    with _deep_lock:
        state = _deep_states.get(universe)
        if state and state.get("status") == "running":
            return {"status": "running", "done": state["done"], "total": state["total"], "universe": universe}

    if not refresh:
        cached = cache_get(f"deep_screener_{CACHE_VERSION}_{universe}")
        if cached:
            return {"status": "done", **cached}

    if refresh:
        # invalida el caché por acción para recalcular de verdad
        for s in UNIVERSES[universe]:
            cache_set(f"deep_{CACHE_VERSION}_{s.replace('/', '_').replace('.', '_')}", None, ttl=0)

    # Re-chequear estado bajo lock para evitar dos workers simultáneos
    with _deep_lock:
        state = _deep_states.get(universe)
        if state and state.get("status") == "running":
            return {"status": "running", "done": state["done"], "total": state["total"], "universe": universe}
        _deep_states[universe] = {
            "status": "running",
            "done": 0,
            "total": len(UNIVERSES[universe]),
            "universe": universe,
        }
    threading.Thread(target=_deep_worker, args=(universe,), daemon=True).start()
    return {"status": "running", "done": 0, "total": len(UNIVERSES[universe]), "universe": universe}
