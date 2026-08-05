"""Historia financiera larga (10-15+ años) desde SEC EDGAR (XBRL company facts).

API oficial y gratuita de la SEC. Solo cubre empresas que reportan en EE.UU.;
para el resto se degrada a los ~4-5 años de Yahoo sin error.
"""

import threading
import time

import pandas as pd
import requests

from .data import cache_get, cache_set

UA = {"User-Agent": "ElInversorInteligente/1.0 (pacortes2021@udec.cl)"}

TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"

_sec_lock = threading.Lock()
_last_sec_req_time = 0.0
MIN_SEC_INTERVAL = 0.11  # Máximo ~9 peticiones/segundo (SEC permite máximo 10 req/s)


def _sec_rate_limit():
    global _last_sec_req_time
    with _sec_lock:
        now = time.time()
        elapsed = now - _last_sec_req_time
        if elapsed < MIN_SEC_INTERVAL:
            time.sleep(MIN_SEC_INTERVAL - elapsed)
        _last_sec_req_time = time.time()


# Orden de preferencia de tags XBRL por métrica (los nombres cambian entre eras)
TAGS = {
    "revenue": ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues",
                "SalesRevenueNet", "SalesRevenueGoodsNet",
                "RevenueFromContractWithCustomerIncludingAssessedTax"],
    "netIncome": ["NetIncomeLoss", "NetIncomeLossAvailableToCommonStockholdersBasic"],
    "eps": ["EarningsPerShareDiluted", "EarningsPerShareBasic"],
    "grossProfit": ["GrossProfit"],
    "opIncome": ["OperatingIncomeLoss"],
    "ocf": ["NetCashProvidedByUsedInOperatingActivities",
            "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"],
    "capex": ["PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets"],
    "equity": ["StockholdersEquity",
               "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"],
    "shares": ["WeightedAverageNumberOfDilutedSharesOutstanding",
               "WeightedAverageNumberOfSharesOutstandingBasic"],
}
INSTANT = {"equity"}          # conceptos de saldo (sin período start-end)
PER_SHARE = {"eps"}           # unidad USD/shares
SHARE_UNITS = {"shares"}      # unidad shares


def _cik_map():
    cached = cache_get("_edgar_ciks")
    if cached is not None:
        return cached or {}
    _sec_rate_limit()
    r = requests.get(TICKERS_URL, headers=UA, timeout=30)
    r.raise_for_status()
    m = {v["ticker"].upper(): v["cik_str"] for v in r.json().values()}
    cache_set("_edgar_ciks", m, ttl=30 * 24 * 3600)
    return m


def _annual_points(units_entry, instant: bool):
    """[(end_iso, val)] anuales de un tag: 10-K/20-F, fp=FY, período ~1 año.
    Por año fiscal se queda con el reporte más reciente (filed)."""
    best = {}  # end_year -> (filed, end, val)
    for u in units_entry:
        if u.get("fp") != "FY" or not str(u.get("form", "")).startswith(("10-K", "20-F", "40-F")):
            continue
        end, val = u.get("end"), u.get("val")
        if end is None or val is None:
            continue
        if not instant:
            start = u.get("start")
            if not start:
                continue
            days = (pd.Timestamp(end) - pd.Timestamp(start)).days
            if not (330 <= days <= 400):
                continue
        year = int(end[:4])
        filed = u.get("filed", "")
        if year not in best or filed > best[year][0]:
            best[year] = (filed, end, float(val))
    return {yr: (end, val) for yr, (filed, end, val) in best.items()}


def _extract(facts):
    """Reduce el companyfacts completo a series anuales pequeñas y cacheables."""
    gaap = facts.get("us-gaap", {})
    out = {}
    for metric, tags in TAGS.items():
        merged = {}  # year -> (end, val); el primer tag en preferencia gana
        for tag in tags:
            node = gaap.get(tag)
            if not node:
                continue
            units = node.get("units", {})
            if metric in PER_SHARE:
                entry = units.get("USD/shares") or units.get("USD")
            elif metric in SHARE_UNITS:
                entry = units.get("shares")
            else:
                entry = units.get("USD")
            if not entry:
                continue
            pts = _annual_points(entry, metric in INSTANT)
            for yr, ev in pts.items():
                merged.setdefault(yr, ev)
        if merged:
            out[metric] = {str(yr): [end, val] for yr, (end, val) in sorted(merged.items())}
    return out


def get_annual_history(symbol: str):
    """Series anuales largas para un símbolo, o None si no está en EDGAR."""
    sym = symbol.upper()
    key = f"edgar_{sym.replace('/', '_').replace('.', '_')}"
    cached = cache_get(key)
    if cached is not None:
        return cached or None  # {} = ya sabemos que no hay datos
    try:
        cik = _cik_map().get(sym)
        if cik is None:
            cache_set(key, {}, ttl=24 * 3600)
            return None
        _sec_rate_limit()
        r = requests.get(FACTS_URL.format(cik=cik), headers=UA, timeout=60)
        r.raise_for_status()
        slim = _extract(r.json().get("facts", {}))
        cache_set(key, slim, ttl=7 * 24 * 3600)
        return slim or None
    except Exception:
        return None


# ------------------------------------------------- conversión a estructuras

def to_series(hist, metric):
    """pd.Series indexada por fecha de cierre fiscal para una métrica."""
    if not hist or metric not in hist:
        return None
    pts = {pd.Timestamp(end): val for end, val in hist[metric].values()}
    return pd.Series(pts).sort_index() if pts else None


def to_annual_rows(hist):
    """Filas anuales con el mismo esquema que metrics.annual_fundamentals
    (los campos que EDGAR no tiene quedan en None)."""
    if not hist:
        return []
    years = set()
    for metric in hist.values():
        years.update(int(y) for y in metric.keys())

    rows = []
    for yr in sorted(years):
        def g(metric):
            v = hist.get(metric, {}).get(str(yr))
            return v[1] if v else None

        def end(metric):
            v = hist.get(metric, {}).get(str(yr))
            return v[0] if v else None

        rev, ni, gp, op = g("revenue"), g("netIncome"), g("grossProfit"), g("opIncome")
        ocf, capex, eq, sh = g("ocf"), g("capex"), g("equity"), g("shares")
        fcf = (ocf - capex) if (ocf is not None and capex is not None) else None
        end_date = end("revenue") or end("netIncome") or end("eps") or end("equity")
        rows.append({
            "year": yr,
            "endDate": int(pd.Timestamp(end_date).timestamp() * 1000) if end_date else None,
            "revenue": rev, "netIncome": ni, "eps": g("eps"),
            "grossMargin": (gp / rev * 100) if (gp is not None and rev) else None,
            "opMargin": (op / rev * 100) if (op is not None and rev) else None,
            "netMargin": (ni / rev * 100) if (ni is not None and rev) else None,
            "ocf": ocf, "capex": (-capex if capex is not None else None), "fcf": fcf,
            "fcfMargin": (fcf / rev * 100) if (fcf is not None and rev) else None,
            "equity": eq, "totalDebt": None, "cash": None,
            "debtToEquity": None, "currentRatio": None,
            "roe": (ni / eq * 100) if (ni is not None and eq and eq > 0) else None,
            "roic": None, "interestCoverage": None,
            "ebitda": None, "debtToEbitda": None,
            "shares": sh, "sharesOut": sh, "dividendPS": None,
            "source": "edgar",
        })
    return rows
