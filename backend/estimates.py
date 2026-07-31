"""Proyecciones de analistas y Growth Grid (estimaciones a futuro)."""

import math
import pandas as pd

from . import metrics as M
from .data import jclean


def _safe_int(v):
    """Convierte a int tolerando NaN/None/cadenas."""
    try:
        f = M._f(v)
        return int(f) if f is not None else None
    except (TypeError, ValueError):
        return None


def _build_growth_grid(raw, info, annuals=None, price=None):
    """Construye la grilla de crecimiento histórico + proyecciones 5 años."""
    if not annuals:
        return None
    curr = info.get("currency") or "USD"
    price_val = price or info.get("currentPrice") or info.get("regularMarketPrice") or 0

    sorted_annuals = sorted(annuals, key=lambda a: a.get("year", 0))[-5:]
    hist_years = [a["year"] for a in sorted_annuals if a.get("year")]
    if not hist_years:
        return None

    last_y = max(hist_years)
    proj_years = [last_y + i for i in range(1, 6)]
    all_years = hist_years + proj_years

    rev_map = {a["year"]: a.get("revenue") for a in sorted_annuals}
    ebitda_map = {
        a["year"]: a.get("ebitda") or (a.get("revenue") * (a.get("opMargin", 20) / 100.0) if a.get("revenue") and a.get("opMargin") else None)
        for a in sorted_annuals
    }
    ni_map = {a["year"]: a.get("netIncome") for a in sorted_annuals}
    eps_map = {a["year"]: a.get("eps") for a in sorted_annuals}
    fcf_map = {a["year"]: a.get("fcf") for a in sorted_annuals}
    div_map = {a["year"]: a.get("dividendPS") for a in sorted_annuals}

    last_y = max(hist_years)
    last_eps = eps_map.get(last_y)
    if last_eps and price_val and info.get("trailingPE"):
        expected_eps = price_val / info["trailingPE"]
        if expected_eps > 0 and (expected_eps / last_eps) >= 5.0:
            scale_factor = round(expected_eps / last_eps)
            for y_k in eps_map:
                if eps_map[y_k] is not None:
                    eps_map[y_k] = round(eps_map[y_k] * scale_factor, 2)

    sh_out = info.get("sharesOutstanding") or 1

    rev_est_df = getattr(raw, "revenue_estimate", None)
    eps_est_df = getattr(raw, "earnings_estimate", None)

    g_rev_1y = 0.08
    if rev_est_df is not None and not rev_est_df.empty and "+1y" in rev_est_df.index:
        v = rev_est_df.loc["+1y", "growth"]
        if pd.notna(v) and v is not None:
            g_rev_1y = float(v)

    g_eps_1y = 0.10
    if eps_est_df is not None and not eps_est_df.empty and "+1y" in eps_est_df.index:
        v = eps_est_df.loc["+1y", "growth"]
        if pd.notna(v) and v is not None:
            g_eps_1y = float(v)

    g_rev_long = max(0.02, g_rev_1y * 0.85) if g_rev_1y > 0 else 0.03
    g_eps_long = max(0.03, g_eps_1y * 0.85) if g_eps_1y > 0 else 0.04

    cur_rev = rev_map.get(last_y) or 0
    cur_ebitda = ebitda_map.get(last_y) or (cur_rev * 0.25)
    cur_ni = ni_map.get(last_y) or (cur_rev * 0.15)
    cur_eps = eps_map.get(last_y) or (cur_ni / sh_out if sh_out else 1.0)
    cur_fcf = fcf_map.get(last_y) or (cur_ni)
    cur_div = div_map.get(last_y) or 0

    rev_all = {**rev_map}
    ebitda_all = {**ebitda_map}
    ni_all = {**ni_map}
    eps_all = {**eps_map}
    fcf_all = {**fcf_map}
    div_all = {**div_map}
    fwd_pe_all = {y: None for y in hist_years}

    base_fwd_pe = M._f(info.get("forwardPE"))
    if not base_fwd_pe and M._f(info.get("trailingPE")):
        base_fwd_pe = M._f(info.get("trailingPE")) / (1 + g_eps_1y) if (1 + g_eps_1y) > 0 else M._f(info.get("trailingPE"))

    for idx, py in enumerate(proj_years):
        g_r = g_rev_1y if idx == 0 else g_rev_long
        g_e = g_eps_1y if idx == 0 else g_eps_long

        cur_rev *= (1 + g_r)
        cur_ebitda *= (1 + g_r)
        cur_ni *= (1 + g_e)
        cur_eps *= (1 + g_e)
        cur_fcf *= (1 + g_e)
        if cur_div and cur_div > 0:
            cur_div *= (1 + g_e)

        rev_all[py] = cur_rev
        ebitda_all[py] = cur_ebitda
        ni_all[py] = cur_ni
        eps_all[py] = cur_eps
        fcf_all[py] = cur_fcf
        div_all[py] = cur_div

        if base_fwd_pe and base_fwd_pe > 0:
            if idx == 0:
                fwd_pe_all[py] = base_fwd_pe
            else:
                prev_pe = fwd_pe_all[proj_years[idx - 1]]
                fwd_pe_all[py] = prev_pe / (1 + g_e) if (1 + g_e) > 0 else prev_pe
        else:
            fwd_pe_all[py] = (price_val / cur_eps) if (price_val and cur_eps > 0) else None

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
        v_end = data_dict.get(proj_years[-1])
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

    return jclean({
        "currency": curr,
        "years": year_headers,
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
    })


def build_estimates_payload(raw, info, annuals=None, price=None):
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
        growth_grid = _build_growth_grid(raw, info, annuals, price)
    except Exception:
        growth_grid = None

    return jclean({
        "recommendations": rec_dict,
        "priceTargets": pt_dict,
        "earningsEstimate": earnings_est,
        "revenueEstimate": revenue_est,
        "growthGrid": growth_grid,
    })