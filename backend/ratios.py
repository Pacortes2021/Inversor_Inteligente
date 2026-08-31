"""Cálculo de ratios comparativos vs sector y promedios históricos."""

import numpy as np
import pandas as pd

from . import metrics as M
from . import valuation as V
from .data import jclean


SECTOR_AVGS = {
    "Technology": {
        "pe": 28.5, "pb": 7.2, "ps": 5.5, "pcf": 20.0, "netMargin": 18.2, "divYield": 0.8,
        "peg": 1.2, "quick": 1.8, "cash": 0.9, "debtToEquity": 0.4, "roe": 22.0,
        "evEbitda": 18.0, "grossMargin": 55.0, "opMargin": 25.0, "roa": 12.0, "roc": 18.0,
    },
    "Communication Services": {
        "pe": 29.55, "pb": 6.67, "ps": 5.13, "pcf": 35.02, "netMargin": 15.5, "divYield": 1.2,
        "peg": 1.1, "quick": 1.2, "cash": 0.8, "debtToEquity": 0.8, "roe": 18.0,
        "evEbitda": 16.0, "grossMargin": 50.0, "opMargin": 22.0, "roa": 8.0, "roc": 15.0,
    },
    "Consumer Cyclical": {
        "pe": 22.0, "pb": 4.8, "ps": 1.8, "pcf": 12.0, "netMargin": 7.5, "divYield": 1.5,
        "peg": 1.3, "quick": 1.1, "cash": 0.5, "debtToEquity": 1.2, "roe": 15.0,
        "evEbitda": 12.0, "grossMargin": 35.0, "opMargin": 12.0, "roa": 6.0, "roc": 12.0,
    },
    "Consumer Defensive": {
        "pe": 21.0, "pb": 5.5, "ps": 1.4, "pcf": 14.5, "netMargin": 6.2, "divYield": 2.6,
        "peg": 1.8, "quick": 0.8, "cash": 0.3, "debtToEquity": 1.8, "roe": 20.0,
        "evEbitda": 14.0, "grossMargin": 30.0, "opMargin": 10.0, "roa": 5.0, "roc": 10.0,
    },
    "Financial Services": {
        "pe": 14.5, "pb": 1.2, "ps": 2.5, "pcf": 9.5, "netMargin": 16.0, "divYield": 3.2,
        "peg": 1.1, "quick": 1.0, "cash": 0.6, "debtToEquity": 1.5, "roe": 12.0,
        "evEbitda": None, "grossMargin": None, "opMargin": None, "roa": 1.0, "roc": 8.0,
    },
    "Healthcare": {
        "pe": 25.0, "pb": 4.5, "ps": 4.0, "pcf": 17.0, "netMargin": 9.8, "divYield": 1.6,
        "peg": 1.4, "quick": 1.5, "cash": 0.7, "debtToEquity": 0.6, "roe": 16.0,
        "evEbitda": 14.0, "grossMargin": 60.0, "opMargin": 20.0, "roa": 7.0, "roc": 13.0,
    },
    "Industrials": {
        "pe": 21.5, "pb": 4.2, "ps": 1.9, "pcf": 14.0, "netMargin": 8.0, "divYield": 1.7,
        "peg": 1.3, "quick": 1.0, "cash": 0.4, "debtToEquity": 0.9, "roe": 17.0,
        "evEbitda": 13.0, "grossMargin": 30.0, "opMargin": 14.0, "roa": 6.0, "roc": 12.0,
    },
    "Basic Materials": {
        "pe": 15.8, "pb": 2.1, "ps": 1.4, "pcf": 9.8, "netMargin": 7.2, "divYield": 2.7,
        "peg": 1.2, "quick": 1.1, "cash": 0.5, "debtToEquity": 0.7, "roe": 11.5,
        "evEbitda": 8.0, "grossMargin": 25.0, "opMargin": 12.0, "roa": 5.0, "roc": 9.0,
    },
    "Energy": {
        "pe": 11.2, "pb": 1.5, "ps": 1.1, "pcf": 5.8, "netMargin": 9.2, "divYield": 4.1,
        "peg": 0.9, "quick": 0.9, "cash": 0.4, "debtToEquity": 0.5, "roe": 14.0,
        "evEbitda": 6.0, "grossMargin": 35.0, "opMargin": 15.0, "roa": 6.0, "roc": 11.0,
    },
    "Utilities": {
        "pe": 17.5, "pb": 1.8, "ps": 2.3, "pcf": 10.5, "netMargin": 9.5, "divYield": 3.7,
        "peg": 2.1, "quick": 0.7, "cash": 0.2, "debtToEquity": 1.6, "roe": 9.8,
        "evEbitda": 10.0, "grossMargin": 40.0, "opMargin": 20.0, "roa": 3.0, "roc": 6.0,
    },
    "Real Estate": {
        "pe": 26.5, "pb": 2.3, "ps": 4.8, "pcf": 15.5, "netMargin": 11.5, "divYield": 4.3,
        "peg": 1.8, "quick": 0.8, "cash": 0.3, "debtToEquity": 2.2, "roe": 8.5,
        "evEbitda": 16.0, "grossMargin": 60.0, "opMargin": 30.0, "roa": 2.0, "roc": 5.0,
    },
}


def _avg_field(annuals, field, last_n=5):
    vals = [a.get(field) for a in annuals[-last_n:] if a.get(field) is not None]
    return sum(vals) / len(vals) if vals else None


def _cagr_10y(annuals, field):
    vals = [a for a in annuals if a.get(field) is not None and a.get(field) > 0]
    if len(vals) >= 6:
        first, last = vals[0][field], vals[-1][field]
        years = max(vals[-1]["year"] - vals[0]["year"], 1)
        return (last / first) ** (1 / years) - 1
    return None


def _ev_ebitda_5y(annuals, prices):
    ev_ebitda_vals = []
    for a in annuals[-5:]:
        ebitda = a.get("ebitda")
        debt_val = a.get("totalDebt") or 0
        cash_val = a.get("cash") or 0
        sh = a.get("sharesOut")
        dt_val = a.get("endDate")
        if ebitda and ebitda > 0 and sh and dt_val:
            dt = pd.to_datetime(dt_val, unit="ms") if isinstance(dt_val, (int, float)) else pd.to_datetime(dt_val)
            if prices is not None and not prices.empty:
                idx = prices.index.get_indexer([dt], method="nearest")[0]
                px = float(prices.iloc[idx]["Close"]) if idx >= 0 else None
                if px:
                    ev_ebitda_vals.append((px * sh + debt_val - cash_val) / ebitda)
    return sum(ev_ebitda_vals) / len(ev_ebitda_vals) if ev_ebitda_vals else None


def _div_yield_5y(annuals, prices):
    div_yield_vals = []
    for a in annuals[-5:]:
        div = a.get("dividendPS")
        dt_val = a.get("endDate")
        if div is not None and dt_val:
            dt = pd.to_datetime(dt_val, unit="ms") if isinstance(dt_val, (int, float)) else pd.to_datetime(dt_val)
            if prices is not None and not prices.empty:
                idx = prices.index.get_indexer([dt], method="nearest")[0]
                px_at_date = float(prices.iloc[idx]["Close"]) if idx >= 0 else None
                if px_at_date:
                    div_yield_vals.append(div / px_at_date * 100)
    return sum(div_yield_vals) / len(div_yield_vals) if div_yield_vals else 0.0


def _pcf_5y(annuals, prices):
    pcf_vals = []
    for a in annuals[-5:]:
        fcf = a.get("fcf")
        sh = a.get("sharesOut")
        dt_val = a.get("endDate")
        if fcf is not None and sh and sh > 0 and dt_val:
            fcf_ps = fcf / sh
            dt = pd.to_datetime(dt_val, unit="ms") if isinstance(dt_val, (int, float)) else pd.to_datetime(dt_val)
            if prices is not None and not prices.empty and fcf_ps > 0:
                idx = prices.index.get_indexer([dt], method="nearest")[0]
                px_at_date = float(prices.iloc[idx]["Close"]) if idx >= 0 else None
                if px_at_date:
                    pcf_vals.append(px_at_date / fcf_ps)
    return sum(pcf_vals) / len(pcf_vals) if pcf_vals else None


def calculate_ratios_payload(price, info, annuals, prices, pe_hist, pb_hist, ps_hist,
                             fcf_ttm_now=None, mc_now=None):
    """Construye el bloque 'ratios' del payload con comparativas sector/5Y."""
    sector_name = info.get("sector") or "Technology"
    sec = SECTOR_AVGS.get(sector_name, SECTOR_AVGS["Technology"])

    now_dt = pd.Timestamp.now()
    five_years_ago_dt = now_dt - pd.DateOffset(years=5)

    pe_5y_avg = float(pe_hist[pe_hist.index >= five_years_ago_dt].mean()) if pe_hist is not None and not pe_hist.empty else None
    pb_5y_avg = float(pb_hist[pb_hist.index >= five_years_ago_dt].mean()) if pb_hist is not None and not pb_hist.empty else None
    ps_5y_avg = float(ps_hist[ps_hist.index >= five_years_ago_dt].mean()) if ps_hist is not None and not ps_hist.empty else None

    last_5_annuals = annuals[-5:] if annuals else []
    net_margin_5y_avg = _avg_field(last_5_annuals, "netMargin")
    roe_5y_avg = _avg_field(last_5_annuals, "roe")
    roic_5y_avg = _avg_field(last_5_annuals, "roic")
    debt_to_equity_5y_avg = _avg_field(last_5_annuals, "debtToEquity")
    current_ratio_5y_avg = _avg_field(last_5_annuals, "currentRatio")
    quick_ratio_5y_avg = current_ratio_5y_avg * 0.75 if current_ratio_5y_avg else None

    gross_margin_5y = _avg_field(last_5_annuals, "grossMargin")
    op_margin_5y = _avg_field(last_5_annuals, "opMargin")

    roa_vals = [a["netIncome"] / a["assets"] * 100 for a in last_5_annuals if a.get("netIncome") and a.get("assets")]
    roa_5y = sum(roa_vals) / len(roa_vals) if roa_vals else None

    ev_ebitda_5y = _ev_ebitda_5y(last_5_annuals, prices)
    div_yield_5y_avg = _div_yield_5y(last_5_annuals, prices)
    pcf_5y_avg = _pcf_5y(last_5_annuals, prices)

    pe_ttm = M._f(info.get("trailingPE"))
    pb_ttm = M._f(info.get("priceToBook"))
    ps_ttm = M._f(info.get("priceToSalesTrailing12Months")) or M._f(info.get("priceToSales"))

    # P/CF actual: usa el FCF TTM computado de estados de flujos si se entregó
    # (misma fuente que el último punto del chart), con fallback al FCF anual.
    fcf_now = fcf_ttm_now or (annuals[-1].get("fcf") if annuals else None)
    mc = mc_now or M._f(info.get("marketCap"))
    fcf_yield = (fcf_now / mc * 100) if (fcf_now and mc) else None
    pcf_ttm = 100.0 / fcf_yield if fcf_yield and fcf_yield > 0 else None

    if pe_ttm is None and pe_hist is not None and not pe_hist.empty:
        pe_ttm = float(pe_hist.iloc[-1])
    if pb_ttm is None and pb_hist is not None and not pb_hist.empty:
        pb_ttm = float(pb_hist.iloc[-1])
    if ps_ttm is None and ps_hist is not None and not ps_hist.empty:
        ps_ttm = float(ps_hist.iloc[-1])

    net_margin_ttm = M._f(info.get("netProfitMargins"))
    if net_margin_ttm is not None:
        net_margin_ttm *= 100
    elif annuals:
        net_margin_ttm = annuals[-1].get("netMargin")

    div_yield_ttm = M._f(info.get("trailingAnnualDividendYield"))
    if div_yield_ttm is not None:
        div_yield_ttm *= 100
    else:
        div_yield_ttm = M._f(info.get("dividendYield"))
        if div_yield_ttm is None and info.get("dividendRate") and price:
            div_yield_ttm = float(info["dividendRate"]) / price * 100
    if div_yield_ttm is None:
        div_yield_ttm = 0.0

    ev_ebitda_ttm = M._f(info.get("enterpriseValueToEbitda"))
    peg_ttm = M._f(info.get("pegRatio"))
    quick_ttm = M._f(info.get("quickRatio"))

    cash_ttm = None
    total_cash = M._f(info.get("totalCash"))
    cur_liab = M._f(info.get("totalCurrentLiabilities"))
    if total_cash is not None and cur_liab:
        cash_ttm = total_cash / cur_liab

    debt_to_equity_ttm = M._f(info.get("debtToEquity"))
    if debt_to_equity_ttm is not None and debt_to_equity_ttm > 5:
        debt_to_equity_ttm /= 100.0

    roe_ttm = M._f(info.get("returnOnEquity"))
    if roe_ttm is not None:
        roe_ttm *= 100
    elif annuals:
        roe_ttm = annuals[-1].get("roe")

    def _calc_fcf_ps(fcf, sh):
        if not fcf or not sh or sh <= 0:
            return None
        val = fcf / sh
        if val > 500:
            val = fcf / (sh * 1_000_000.0)
        elif val > 50:
            val = fcf / (sh * 1_000.0)
        return round(val, 2) if (val and val > 0 and val < 500) else None

    shares_now = M._f(info.get("sharesOutstanding"))
    fcf_ps_ttm = _calc_fcf_ps(fcf_now, shares_now) if (fcf_now and shares_now) else None

    fcf_ps_vals = []
    for a in last_5_annuals:
        fps = _calc_fcf_ps(a.get("fcf"), a.get("sharesOut"))
        if fps:
            fcf_ps_vals.append(fps)
    fcf_ps_5y_avg = round(sum(fcf_ps_vals) / len(fcf_ps_vals), 2) if fcf_ps_vals else None

    roc_ttm = V.greenblatt_roc(info, annuals)

    return jclean({
        "sectorName": sector_name,
        "pe": {"val": pe_ttm, "sector": sec["pe"], "avg5y": pe_5y_avg},
        "pb": {"val": pb_ttm, "sector": sec["pb"], "avg5y": pb_5y_avg},
        "ps": {"val": ps_ttm, "sector": sec["ps"], "avg5y": ps_5y_avg},
        "pcf": {"val": pcf_ttm, "sector": sec["pcf"], "avg5y": pcf_5y_avg},
        "netMargin": {"val": net_margin_ttm, "sector": sec["netMargin"], "avg5y": net_margin_5y_avg},
        "divYield": {"val": div_yield_ttm, "sector": sec["divYield"], "avg5y": div_yield_5y_avg},
        "peg": {"val": peg_ttm, "sector": sec["peg"], "avg5y": None},
        "quick": {"val": quick_ttm, "sector": sec["quick"], "avg5y": quick_ratio_5y_avg},
        "cash": {"val": cash_ttm, "sector": sec["cash"], "avg5y": (current_ratio_5y_avg * 0.35 if current_ratio_5y_avg else None)},
        "debtToEquity": {"val": debt_to_equity_ttm, "sector": sec["debtToEquity"], "avg5y": debt_to_equity_5y_avg},
        "roe": {"val": roe_ttm, "sector": sec["roe"], "avg5y": roe_5y_avg},
        "fcfPs": {"val": fcf_ps_ttm, "sector": None, "avg5y": fcf_ps_5y_avg},
        "evEbitda": {"val": ev_ebitda_ttm, "sector": sec.get("evEbitda") or 15.0, "avg5y": ev_ebitda_5y},
        "grossMargin": {
            "val": (M._f(info.get("grossMargins")) * 100 if M._f(info.get("grossMargins")) else (annuals[-1].get("grossMargin") if annuals else None)),
            "sector": sec.get("grossMargin") or 40.0,
            "avg5y": gross_margin_5y,
        },
        "opMargin": {
            "val": (M._f(info.get("operatingMargins")) * 100 if M._f(info.get("operatingMargins")) else (annuals[-1].get("opMargin") if annuals else None)),
            "sector": sec.get("opMargin") or 12.0,
            "avg5y": op_margin_5y,
        },
        "roa": {
            "val": (M._f(info.get("returnOnAssets")) * 100 if M._f(info.get("returnOnAssets")) else (annuals[-1].get("netIncome") / annuals[-1].get("assets") * 100 if annuals and annuals[-1].get("netIncome") and annuals[-1].get("assets") else None)),
            "sector": sec.get("roa") or 8.0,
            "avg5y": roa_5y,
        },
        "roc": {"val": roc_ttm, "sector": sec.get("roe") * 0.9 if sec.get("roe") else 15.0, "avg5y": roic_5y_avg},
        "roic10yAvg": roic_5y_avg,
        "revGrowth10y": _cagr_10y(annuals, "revenue"),
        "netIncomeGrowth10y": _cagr_10y(annuals, "netIncome"),
        "fcfGrowth10y": _cagr_10y(annuals, "fcf"),
    })