"""Cliente de Financial Modeling Prep (FMP) para estimaciones forward de
analistas (revenue, EPS, EBITDA, EBIT, net income) usadas para proyectar
los flujos de caja futuros del DCF. Fallback silencioso si no hay clave,
el símbolo no está cubierto o FMP falla (la app sigue con Yahoo)."""

import json
import math
import time
import urllib.parse
import urllib.request

from .config import FMP_API_KEY, FMP_TIMEOUT, FMP_TTL

_cache = {}  # sym -> (ts, rows|None)


def _f(x):
    if x is None:
        return None
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def fmp_symbol(yahoo_symbol):
    """Traduce un símbolo de Yahoo a la convención de FMP (solo sufijos
    de intercambio comunes; EE.UU. y la mayoría quedan igual)."""
    s = str(yahoo_symbol).upper()
    if s.endswith(".SN"):
        return s[:-3] + ".CL"   # Chile
    if s.endswith(".DE"):
        return s[:-3] + ".F"    # Alemania (XETRA)
    if s.endswith(".TO"):
        return s[:-3] + ".T"    # Canadá (Toronto)
    if s.endswith(".L"):
        return s[:-2] + ".LSE"  # Reino Unido
    if s.endswith(".PA"):
        return s[:-3] + ".EPA"  # París
    return s


def fetch_analyst_estimates(yahoo_symbol, timeout=None):
    """Estimaciones anuales de consenso forward. Devuelve lista ordenada
    ascendente por ejercicio fiscal de dicts:
      {"year": "2027", "revenueAvg": .., "netIncomeAvg": .., "epsAvg": ..,
       "ebitdaAvg": .., "analysts": N}
    o None si no hay clave/cobertura/error."""
    if not FMP_API_KEY:
        return None
    sym = fmp_symbol(yahoo_symbol)
    now = time.time()
    if sym in _cache and now - _cache[sym][0] < FMP_TTL:
        return _cache[sym][1]

    url = ("https://financialmodelingprep.com/stable/analyst-estimates"
           f"?symbol={urllib.parse.quote(sym)}&period=annual&limit=10"
           f"&apikey={urllib.parse.quote(FMP_API_KEY)}")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ElInversorInteligente/1.0"})
        with urllib.request.urlopen(req, timeout=timeout or FMP_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8", "replace"))
    except Exception:
        _cache[sym] = (now, None)
        return None

    if not isinstance(data, list) or not data:
        _cache[sym] = (now, None)
        return None

    rows = []
    seen_years = set()
    for item in data:
        if not isinstance(item, dict):
            continue
        date = str(item.get("date") or item.get("period") or "").strip()
        year = date[:4] if date else ""
        ni = _f(item.get("estimatedNetIncomeAvg"))
        rev = _f(item.get("estimatedRevenueAvg"))
        if not year or not year.isdigit() or (ni is None and rev is None):
            continue
        if year in seen_years:
            continue
        seen_years.add(year)
        n_analysts = 0
        for k in ("numberOfAnalystEstimatedRevenues", "numberOfAnalystEstimatedEps",
                  "numberOfAnalystEstimatedEbitda"):
            if _f(item.get(k)) is not None:
                n_analysts = max(n_analysts, int(item.get(k)))
        rows.append({
            "year": year,
            "revenueAvg": rev,
            "netIncomeAvg": ni,
            "epsAvg": _f(item.get("estimatedEps")),
            "ebitdaAvg": _f(item.get("estimatedEbitdaAvg")),
            "analysts": n_analysts,
        })
    rows.sort(key=lambda r: r["year"])
    result = rows if len(rows) >= 1 else None
    _cache[sym] = (now, result)
    return result
