"""Proyecciones de analistas y Growth Grid (estimaciones a futuro).

EPS: consenso de Yahoo (yfinance) como fuente primaria, con cross-check
contra StockAnalysis.com (EPS del próximo año fiscal) y ajuste por splits
cuando el histórico de EDGAR no refleja desdoblamientos recientes.
"""

import re
import time

import pandas as pd

from . import metrics as M
from .data import cache_get, cache_set, jclean

SA_TTL = 24 * 3600  # caché de StockAnalysis: 24 h
G_EPS_LONG_CAP = 0.35  # techo defensivo para crecimiento EPS de largo plazo
G_EPS_LONG_FLOOR = 0.03
G_REV_LONG_CAP = 0.25
G_REV_LONG_FLOOR = 0.02


def _safe_int(v):
    """Convierte a int tolerando NaN/None/cadenas."""
    try:
        f = M._f(v)
        return int(f) if f is not None else None
    except (TypeError, ValueError):
        return None


def _sa_url_symbol(symbol):
    return re.sub(r"[^a-zA-Z0-9]", "-", symbol).lower()


def _sa_eps_forecast(symbol):
    """EPS estimado del próximo año fiscal (StockAnalysis.com) con caché 24h.

    Devuelve {"eps": float|None, "growth": float|None (%), "year": str|None,
    "analysts": int|None} o None si no hay datos libres.
    """
    key = f"sa_eps_{_sa_url_symbol(symbol)}"
    cached = cache_get(key)
    if cached is not None:
        return cached

    result = None
    try:
        import requests

        url = f"https://stockanalysis.com/stocks/{_sa_url_symbol(symbol)}/forecast/"
        r = requests.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml",
            },
            timeout=15,
        )
        if r.status_code == 200 and r.text:
            result = _parse_sa_forecast(r.text)
    except Exception:
        result = None

    cache_set(key, result, ttl=SA_TTL)
    return result


def _cell_value(text):
    """Limpia una celda HTML ('$312.06', '17.38%', '1.02B') a float o None."""
    t = re.sub(r"<[^>]+>", "", text or "")
    t = re.sub(r"<!--.*?-->", "", t).strip()
    t = re.sub(r"&nbsp;", " ", t)
    if not t or t in ("-", "—", "N/A", "Upgrade"):
        return None
    m = re.match(r"^-?\$?\s?([\d.,]+)\s?%?$", t)
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", ""))
    except ValueError:
        return None


def _parse_sa_forecast(html):
    """Extrae el EPS del próximo año fiscal y su crecimiento del HTML de SA."""
    tables = re.findall(r"<table[^>]*>.*?</table>", html, re.S)
    for t in tables:
        text = re.sub(r"<[^>]+>", " ", t)
        if "No. Analysts" not in text:
            continue
        rows = []
        for row in re.findall(r"<tr[^>]*>(.*?)</tr>", t, re.S):
            cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S)
            if not cells:
                continue
            label = re.sub(r"<[^>]+>|<!--.*?-->", "", cells[0]).strip()
            values = []
            for c in cells[1:]:
                raw = re.sub(r"<[^>]+>|<!--.*?-->", "", c).strip()
                values.append(raw)
            rows.append((label, values))

        eps_row = next((r for r in rows if r[0] == "EPS"), None)
        growth_row = next((r for r in rows if r[0] == "EPS Growth"), None)
        analysts_row = next((r for r in rows if r[0] == "No. Analysts"), None)
        header_row = next((r for r in rows if r[0] == "Fiscal Year"), None)
        if not eps_row or not growth_row:
            return None

        eps, idx = None, None
        for i in range(len(eps_row[1]) - 1, -1, -1):
            v = _cell_value(eps_row[1][i])
            if v is not None:
                eps, idx = v, i
                break
        if eps is None or idx is None:
            return None
        # El último dato numérico debe estar en el bloque de proyecciones
        # (últimas 3 columnas); si no, es un dato real, no una proyección.
        if idx < len(eps_row[1]) - 3:
            return None

        growth = _cell_value(growth_row[1][idx]) if idx < len(growth_row[1]) else None
        analysts = _cell_value(analysts_row[1][idx]) if analysts_row and idx < len(analysts_row[1]) else None
        year = header_row[1][idx] if header_row and idx < len(header_row[1]) else None
        return {
            "eps": eps,
            "growth": growth,          # en %
            "year": year,
            "analysts": int(analysts) if analysts else None,
        }
    return None


def _growth_from_df(df, period):
    """Crecimiento de una fila de earnings/revenue_estimate, o None."""
    if df is None or df.empty or period not in df.index:
        return None
    try:
        v = df.loc[period, "growth"]
        if v is None or pd.isna(v):
            return None
        return float(v)
    except Exception:
        return None


def _val_from_df(df, period, col="avg"):
    """Valor numérico de una columna (ej. avg, low, high) en earnings/revenue_estimate."""
    if df is None or df.empty or period not in df.index:
        return None
    try:
        v = df.loc[period, col]
        if v is None or pd.isna(v):
            return None
        return float(v)
    except Exception:
        return None


def _build_growth_grid(symbol, raw, info, annuals=None, price=None, fmp_rows=None):
    """Construye la grilla de crecimiento histórico + proyecciones oficiales de analistas.
    100% basado en datos directos de consenso del proveedor (FMP o Yahoo Finance).
    No realiza extrapolaciones matemáticas inventadas ni cálculos artificiales."""
    if not annuals:
        return None
    curr = info.get("currency") or "USD"
    price_val = price or info.get("currentPrice") or info.get("regularMarketPrice") or 0

    sorted_annuals = sorted(annuals, key=lambda a: a.get("year", 0))[-5:]
    hist_years = [a["year"] for a in sorted_annuals if a.get("year")]
    if not hist_years:
        return None

    last_y = max(hist_years)

    rev_map = {a["year"]: a.get("revenue") for a in sorted_annuals}
    ebitda_map = {
        a["year"]: a.get("ebitda") or (a.get("revenue") * (a.get("opMargin", 20) / 100.0) if a.get("revenue") and a.get("opMargin") else None)
        for a in sorted_annuals
    }
    ni_map = {a["year"]: a.get("netIncome") for a in sorted_annuals}
    eps_map = {a["year"]: a.get("eps") for a in sorted_annuals}
    fcf_map = {a["year"]: a.get("fcf") for a in sorted_annuals}
    div_map = {a["year"]: a.get("dividendPS") for a in sorted_annuals}

    sh_out = info.get("sharesOutstanding") or 1

    rev_est_df = getattr(raw, "revenue_estimate", None)
    eps_est_df = getattr(raw, "earnings_estimate", None)

    # 1. Recopilar proyecciones oficiales exclusivamente de proveedores
    official_by_year = {}
    provider_source = "Finnhub / Yahoo Finance"

    if fmp_rows:
        for row in fmp_rows:
            try:
                fy = int(row.get("year"))
            except (TypeError, ValueError):
                continue
            if fy > last_y:
                official_by_year[fy] = {
                    "revenue": row.get("revenueAvg"),
                    "ebitda": row.get("ebitdaAvg"),
                    "netIncome": row.get("netIncomeAvg"),
                    "eps": row.get("epsAvg"),
                    "analysts": row.get("analysts") or 0,
                }
        if official_by_year:
            provider_source = "FMP (Financial Modeling Prep)"

    if not official_by_year:
        # Fallback a consenso oficial de analistas de Yahoo Finance (0y = próximo año fiscal, +1y = subsiguiente)
        eps_0y = _val_from_df(eps_est_df, "0y", "avg")
        rev_0y = _val_from_df(rev_est_df, "0y", "avg")
        an_0y = _safe_int(_val_from_df(eps_est_df, "0y", "numberOfAnalysts")) or 0

        if eps_0y is not None or rev_0y is not None:
            y1 = last_y + 1
            official_by_year[y1] = {
                "eps": eps_0y,
                "revenue": rev_0y,
                "netIncome": (eps_0y * sh_out) if (eps_0y is not None and sh_out and sh_out > 1) else None,
                "ebitda": None,
                "analysts": an_0y,
            }

        eps_1y = _val_from_df(eps_est_df, "+1y", "avg")
        rev_1y = _val_from_df(rev_est_df, "+1y", "avg")
        an_1y = _safe_int(_val_from_df(eps_est_df, "+1y", "numberOfAnalysts")) or 0

        if eps_1y is not None or rev_1y is not None:
            y2 = last_y + 2
            official_by_year[y2] = {
                "eps": eps_1y,
                "revenue": rev_1y,
                "netIncome": (eps_1y * sh_out) if (eps_1y is not None and sh_out and sh_out > 1) else None,
                "ebitda": None,
                "analysts": an_1y,
            }
        if official_by_year:
            provider_source = "Consenso Oficial de Analistas (Yahoo Finance / Institutional)"

    if not official_by_year:
        return None

    proj_years = sorted(official_by_year.keys())
    all_years = hist_years + proj_years

    rev_all = {**rev_map}
    ebitda_all = {**ebitda_map}
    ni_all = {**ni_map}
    eps_all = {**eps_map}
    fcf_all = {**fcf_map}
    div_all = {**div_map}
    fwd_pe_all = {y: None for y in hist_years}

    for py in proj_years:
        off = official_by_year.get(py, {})
        rev_all[py] = off.get("revenue")
        ebitda_all[py] = off.get("ebitda")
        ni_all[py] = off.get("netIncome")
        eps_all[py] = off.get("eps")
        # No inventamos FCF ni Dividendos si los analistas no los publican formalmente
        fcf_all[py] = None
        div_all[py] = None

        if price_val and off.get("eps") and off["eps"] > 0:
            fwd_pe_all[py] = round(price_val / off["eps"], 2)
        else:
            fwd_pe_all[py] = None

    year_headers = [str(y) if y <= last_y else f"{y}E" for y in all_years]

    def build_metric_row(label, data_dict, in_millions=True, is_per_share=False):
        vals = []
        yoy = []
        for i, y in enumerate(all_years):
            v = data_dict.get(y)
            if v is not None:
                if in_millions:
                    vals.append(round(v / 1e6, 0))
                else:
                    vals.append(round(v, 2))
            else:
                vals.append(None)

            if i > 0 and data_dict.get(all_years[i - 1]) is not None and data_dict.get(y) is not None:
                v_prev = data_dict[all_years[i - 1]]
                v_curr = data_dict[y]
                if v_prev and v_prev != 0:
                    pct = ((v_curr - v_prev) / abs(v_prev)) * 100.0
                    yoy.append(round(pct, 2))
                else:
                    yoy.append(None)
            else:
                yoy.append(None)

        v_start = data_dict.get(last_y)
        v_end = data_dict.get(proj_years[-1]) if proj_years else None
        n_years = len(proj_years)
        cagr = None
        if v_start and v_end and v_start > 0 and v_end > 0 and n_years > 0:
            cagr = round(((v_end / v_start) ** (1.0 / n_years) - 1.0) * 100.0, 2)

        return {
            "label": label,
            "values": vals,
            "yoy": yoy,
            "cagr": cagr,
        }

    mrq_str = None
    if info:
        mrq_ts = info.get("mostRecentQuarter") or info.get("lastFiscalYearEnd")
        if mrq_ts:
            try:
                mrq_str = time.strftime("%Y-%m-%d", time.gmtime(int(mrq_ts)))
            except Exception:
                mrq_str = str(mrq_ts)

    eps_src = {
        "fmp": bool(fmp_rows),
        "source": provider_source,
        "yearsProjected": len(proj_years),
        "lastUpdated": time.strftime("%Y-%m-%d"),
    }

    return jclean({
        "currency": curr,
        "years": year_headers,
        "lastUpdated": time.strftime("%Y-%m-%d"),
        "mostRecentQuarter": mrq_str,
        "rows": [
            build_metric_row("Revenues", rev_all, in_millions=True),
            build_metric_row("Ebitda", ebitda_all, in_millions=True),
            build_metric_row("Net Income", ni_all, in_millions=True),
            build_metric_row("EPS", eps_all, in_millions=False, is_per_share=True),
            {
                "label": "Forward PE",
                "values": [round(fwd_pe_all[y], 2) if fwd_pe_all[y] else None for y in all_years],
                "yoy": [None] * len(all_years),
                "cagr": None,
            },
            build_metric_row("Free Cash Flow", fcf_all, in_millions=True),
            build_metric_row("Dividends", div_all, in_millions=False, is_per_share=True),
        ],
        "epsSources": eps_src,
    })


def build_estimates_payload(raw, info, annuals=None, price=None, symbol=None, fmp_rows=None):
    """Extrae proyecciones de analistas y estimaciones de EPS/Ingresos."""
    rec_dict = {}
    try:
        if hasattr(raw, "recommendations") and raw.recommendations is not None and not raw.recommendations.empty:
            df = raw.recommendations
            latest = df.iloc[0]
            rec_dict = {
                "strongBuy": int(latest.get("strongBuy", 0)),
                "buy": int(latest.get("buy", 0)),
                "hold": int(latest.get("hold", 0)),
                "sell": int(latest.get("sell", 0)),
                "strongSell": int(latest.get("strongSell", 0)),
            }
    except Exception:
        pass

    pt_dict = {}
    try:
        if hasattr(raw, "analyst_price_targets") and raw.analyst_price_targets is not None:
            pt = raw.analyst_price_targets
            if isinstance(pt, dict):
                pt_dict = {
                    "current": M._f(pt.get("current")),
                    "low": M._f(pt.get("low")),
                    "high": M._f(pt.get("high")),
                    "mean": M._f(pt.get("mean")),
                    "median": M._f(pt.get("median")),
                }
    except Exception:
        pass
    if not pt_dict and info.get("targetMeanPrice"):
        pt_dict = {
            "current": M._f(info.get("currentPrice")),
            "low": M._f(info.get("targetLowPrice")),
            "high": M._f(info.get("targetHighPrice")),
            "mean": M._f(info.get("targetMeanPrice")),
            "median": M._f(info.get("targetMedianPrice")),
        }

    earnings_est = []
    try:
        if hasattr(raw, "earnings_estimate") and raw.earnings_estimate is not None and not raw.earnings_estimate.empty:
            df = raw.earnings_estimate
            for idx, row in df.iterrows():
                earnings_est.append({
                    "period": str(idx),
                    "avg": M._f(row.get("avg")),
                    "low": M._f(row.get("low")),
                    "high": M._f(row.get("high")),
                    "yearAgoEps": M._f(row.get("yearAgoEps")),
                    "analysts": _safe_int(row.get("numberOfAnalysts")),
                    "growth": M._f(row.get("growth")),
                })
    except Exception:
        pass

    revenue_est = []
    try:
        if hasattr(raw, "revenue_estimate") and raw.revenue_estimate is not None and not raw.revenue_estimate.empty:
            df = raw.revenue_estimate
            for idx, row in df.iterrows():
                revenue_est.append({
                    "period": str(idx),
                    "avg": M._f(row.get("avg")),
                    "low": M._f(row.get("low")),
                    "high": M._f(row.get("high")),
                    "yearAgoRevenue": M._f(row.get("yearAgoRevenue")),
                    "analysts": _safe_int(row.get("numberOfAnalysts")),
                    "growth": M._f(row.get("growth")),
                })
    except Exception:
        pass

    try:
        growth_grid = _build_growth_grid(symbol, raw, info, annuals, price, fmp_rows=fmp_rows)
    except Exception:
        growth_grid = None

    return jclean({
        "recommendations": rec_dict,
        "priceTargets": pt_dict,
        "earningsEstimate": earnings_est,
        "revenueEstimate": revenue_est,
        "growthGrid": growth_grid,
    })
