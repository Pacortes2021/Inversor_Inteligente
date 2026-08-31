"""Compone el payload completo de análisis para un símbolo."""

from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd

from . import edgar as E
from . import fmp as F
from . import metrics as M
from . import quality as Q
from . import snapshots as S
from . import valuation as V
from .data import RawData, bond_yield_10y, cache_get, cache_set, jclean
from .estimates import build_estimates_payload
from .insiders import build_insiders_holders_payload
from .ratios import calculate_ratios_payload

MAX_HISTORY_YEARS = 16


def _merge_annuals(yahoo_rows, edgar_rows, dividends, splits=None):
    """Años de Yahoo (más completos) + años antiguos que solo tiene EDGAR.
    Los valores por acción de EDGAR se ajustan por splits a la base actual."""
    min_year = pd.Timestamp.now().year - MAX_HISTORY_YEARS
    yahoo_rows_valid = [a for a in yahoo_rows if a.get("revenue") is not None or a.get("netIncome") is not None]
    yahoo_years = {a["year"] for a in yahoo_rows_valid}
    rows = [r for r in edgar_rows if r["year"] not in yahoo_years and r["year"] >= min_year]
    for r in rows:
        if r.get("endDate"):
            f = M.split_factor(splits, pd.Timestamp(r["endDate"], unit="ms"))
            if r.get("eps") is not None:
                r["eps"] = r["eps"] / f
            if r.get("sharesOut") is not None:
                r["sharesOut"] = r["sharesOut"] * f
    rows += yahoo_rows_valid
    rows.sort(key=lambda r: r["year"])

    if dividends is not None and not dividends.empty:
        div_by_year = dividends.groupby(dividends.index.year).sum().to_dict()
        for r in rows:
            if r.get("dividendPS") is None:
                r["dividendPS"] = div_by_year.get(r["year"])
    return rows


def _growth_table(annuals):
    """CAGR a 1/3/5/10 años por métrica clave (estilo QuickFS)."""
    metrics = [("revenue", "Ingresos"), ("netIncome", "Utilidad neta"), ("eps", "EPS"),
               ("fcf", "Flujo de caja libre"), ("dividendPS", "Dividendo/acción"),
               ("equity", "Patrimonio (valor libro)")]
    out = []
    for key, label in metrics:
        vals = {a["year"]: a[key] for a in annuals if a.get(key) is not None}
        if len(vals) < 2:
            continue
        last_year = max(vals)
        end_v = vals[last_year]
        row = {"metric": label, "lastYear": last_year, "current": end_v}
        has_any = False
        for n in (1, 3, 5, 10):
            v0 = vals.get(last_year - n)
            if v0 and v0 > 0 and end_v and end_v > 0:
                row[f"cagr{n}"] = round(((end_v / v0) ** (1 / n) - 1) * 100, 1)
                has_any = True
            else:
                row[f"cagr{n}"] = None
        if has_any:
            out.append(row)
    return out


def _dividend_safety(annuals, dividends_annual, info):
    """Racha de años pagando/subiendo dividendo y payout sobre FCF."""
    cur_year = pd.Timestamp.now().year
    dmap = {item[0]: item[1] for item in dividends_annual if item[0] < cur_year and item[1] > 0}
    if not dmap:
        return None

    paying = 0
    y = cur_year - 1
    while y in dmap:
        paying += 1
        y -= 1

    growing = 0
    y = cur_year - 1
    while y in dmap and (y - 1) in dmap and dmap[y] > dmap[y - 1] * 1.0001:
        growing += 1
        y -= 1

    ratios = []
    for a in annuals[-4:]:
        dps, sh, fcf = a.get("dividendPS"), a.get("sharesOut"), a.get("fcf")
        if dps and sh and fcf and fcf > 0:
            ratios.append(dps * sh / fcf * 100)
    payout_fcf = sorted(ratios)[len(ratios) // 2] if ratios else None
    payout_eps = M._f(info.get("payoutRatio"))
    payout_eps = payout_eps * 100 if payout_eps is not None else None

    ref = payout_fcf if payout_fcf is not None else payout_eps
    if ref is None:
        level, label = "na", "Sin datos de payout"
    elif ref < 60 and paying >= 10:
        level, label = "hi", "Sólido"
    elif ref < 80:
        level, label = "mid", "Razonable"
    else:
        level, label = "lo", "Tensionado"

    return {
        "payingStreak": paying,
        "growthStreak": growing,
        "payoutFcf": round(payout_fcf, 1) if payout_fcf is not None else None,
        "payoutEps": round(payout_eps, 1) if payout_eps is not None else None,
        "level": level,
        "label": label,
    }


def _sec_context(symbol, calendar):
    """Próxima fecha de resultados y links a los informes en EDGAR."""
    next_earnings = None
    next_earnings_est = None
    filings = None
    try:
        eds = calendar.get("Earnings Date") or []
        if eds:
            next_earnings = pd.Timestamp(eds[0]).strftime("%Y-%m-%d")
        est_avg = calendar.get("Earnings Average")
        if est_avg is not None:
            if isinstance(est_avg, (list, tuple)):
                est_avg = est_avg[0]
            next_earnings_est = float(est_avg)
    except Exception:
        pass
    try:
        cik = E._cik_map().get(symbol.upper())
        if cik:
            base = ("https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany"
                    f"&CIK={cik:010d}&owner=include&count=10&type=")
            filings = {"annual": base + "10-K", "quarterly": base + "10-Q"}
    except Exception:
        pass
    return next_earnings, next_earnings_est, filings

def _build_earnings_surprises(earnings_dates_df):
    """Extrae las sorpresas EPS trimestrales (últimos 4-5 trimestres)"""
    surprises = []
    try:
        if earnings_dates_df is not None and not earnings_dates_df.empty:
            df = earnings_dates_df.dropna(subset=['Reported EPS']).head(5)
            for idx, row in df.iterrows():
                surprises.append({
                    "date": str(idx)[:10],
                    "estimate": M._f(row.get("EPS Estimate")),
                    "reported": M._f(row.get("Reported EPS")),
                    "surprise": M._f(row.get("Surprise(%)"))
                })
    except Exception:
        pass
    # Devolver orden cronológico ascendente (el más viejo primero)
    return surprises[::-1]

def _calculate_ratios_payload(price, info, annuals, prices, pe_hist, pb_hist, ps_hist,
                              fcf_ttm_now=None, mc_now=None):
    import numpy as np
    sector_name = info.get("sector") or "Technology"
    sector_avgs = {
        "Technology": {
            "pe": 28.5, "pb": 7.2, "ps": 5.5, "pcf": 20.0, "netMargin": 18.2, "divYield": 0.8,
            "peg": 1.2, "quick": 1.8, "cash": 0.9, "debtToEquity": 0.4, "roe": 22.0
        },
        "Communication Services": {
            "pe": 29.55, "pb": 6.67, "ps": 5.13, "pcf": 35.02, "netMargin": 15.5, "divYield": 1.2,
            "peg": 1.1, "quick": 1.2, "cash": 0.8, "debtToEquity": 0.8, "roe": 18.0
        },
        "Consumer Cyclical": {
            "pe": 22.0, "pb": 4.8, "ps": 1.8, "pcf": 12.0, "netMargin": 7.5, "divYield": 1.5,
            "peg": 1.3, "quick": 1.1, "cash": 0.5, "debtToEquity": 1.2, "roe": 15.0
        },
        "Consumer Defensive": {
            "pe": 21.0, "pb": 5.5, "ps": 1.4, "pcf": 14.5, "netMargin": 6.2, "divYield": 2.6,
            "peg": 1.8, "quick": 0.8, "cash": 0.3, "debtToEquity": 1.8, "roe": 20.0
        },
        "Financial Services": {
            "pe": 14.5, "pb": 1.2, "ps": 2.5, "pcf": 9.5, "netMargin": 16.0, "divYield": 3.2,
            "peg": 1.1, "quick": 1.0, "cash": 0.6, "debtToEquity": 1.5, "roe": 12.0
        },
        "Healthcare": {
            "pe": 25.0, "pb": 4.5, "ps": 4.0, "pcf": 17.0, "netMargin": 9.8, "divYield": 1.6,
            "peg": 1.4, "quick": 1.5, "cash": 0.7, "debtToEquity": 0.6, "roe": 16.0
        },
        "Industrials": {
            "pe": 21.5, "pb": 4.2, "ps": 1.9, "pcf": 14.0, "netMargin": 8.0, "divYield": 1.7,
            "peg": 1.3, "quick": 1.0, "cash": 0.4, "debtToEquity": 0.9, "roe": 17.0
        },
        "Basic Materials": {
            "pe": 15.8, "pb": 2.1, "ps": 1.4, "pcf": 9.8, "netMargin": 7.2, "divYield": 2.7,
            "peg": 1.2, "quick": 1.1, "cash": 0.5, "debtToEquity": 0.7, "roe": 11.5
        },
        "Energy": {
            "pe": 11.2, "pb": 1.5, "ps": 1.1, "pcf": 5.8, "netMargin": 9.2, "divYield": 4.1,
            "peg": 0.9, "quick": 0.9, "cash": 0.4, "debtToEquity": 0.5, "roe": 14.0
        },
        "Utilities": {
            "pe": 17.5, "pb": 1.8, "ps": 2.3, "pcf": 10.5, "netMargin": 9.5, "divYield": 3.7,
            "peg": 2.1, "quick": 0.7, "cash": 0.2, "debtToEquity": 1.6, "roe": 9.8
        },
        "Real Estate": {
            "pe": 26.5, "pb": 2.3, "ps": 4.8, "pcf": 15.5, "netMargin": 11.5, "divYield": 4.3,
            "peg": 1.8, "quick": 0.8, "cash": 0.3, "debtToEquity": 2.2, "roe": 8.5
        }
    }
    sec = sector_avgs.get(sector_name, sector_avgs["Technology"])
    
    now_dt = pd.Timestamp.now()
    five_years_ago_dt = now_dt - pd.DateOffset(years=5)
    
    pe_5y_avg = float(pe_hist[pe_hist.index >= five_years_ago_dt].mean()) if pe_hist is not None and not pe_hist.empty else None
    pb_5y_avg = float(pb_hist[pb_hist.index >= five_years_ago_dt].mean()) if pb_hist is not None and not pb_hist.empty else None
    ps_5y_avg = float(ps_hist[ps_hist.index >= five_years_ago_dt].mean()) if ps_hist is not None and not ps_hist.empty else None
    
    last_5_annuals = annuals[-5:] if annuals else []
    def avg_field(field):
        vals = [a.get(field) for a in last_5_annuals if a.get(field) is not None]
        return sum(vals) / len(vals) if vals else None

    def cagr_10y(field):
        vals = [a for a in annuals if a.get(field) is not None and a.get(field) > 0]
        if len(vals) >= 6:
            first, last = vals[0][field], vals[-1][field]
            years = max(vals[-1]["year"] - vals[0]["year"], 1)
            return (last / first) ** (1 / years) - 1
        return None

    net_margin_5y_avg = avg_field("netMargin")
    roe_5y_avg = avg_field("roe")
    roic_5y_avg = avg_field("roic")
    debt_to_equity_5y_avg = avg_field("debtToEquity")
    current_ratio_5y_avg = avg_field("currentRatio")
    quick_ratio_5y_avg = current_ratio_5y_avg * 0.75 if current_ratio_5y_avg else None
    
    gross_margin_5y = avg_field("grossMargin")
    op_margin_5y = avg_field("opMargin")
    
    roa_vals = [a["netIncome"] / a["assets"] * 100 for a in last_5_annuals if a.get("netIncome") and a.get("assets")]
    roa_5y = sum(roa_vals) / len(roa_vals) if roa_vals else None
    
    # evEbitda 5Y
    ev_ebitda_vals = []
    for a in last_5_annuals:
        ebitda = a.get("ebitda")
        debt_val = a.get("totalDebt") or 0
        cash_val = a.get("cash") or 0
        sh = a.get("sharesOut")
        dt_val = a.get("endDate")
        if ebitda and ebitda > 0 and sh and dt_val:
            dt = pd.to_datetime(dt_val, unit='ms') if isinstance(dt_val, (int, float)) else pd.to_datetime(dt_val)
            if prices is not None and not prices.empty:
                idx = prices.index.get_indexer([dt], method='nearest')[0]
                px = float(prices.iloc[idx]["Close"]) if idx >= 0 else price
                ev_ebitda_vals.append((px * sh + debt_val - cash_val) / ebitda)
    ev_ebitda_5y = sum(ev_ebitda_vals) / len(ev_ebitda_vals) if ev_ebitda_vals else None

    div_yield_vals = []
    for a in last_5_annuals:
        div = a.get("dividendPS")
        dt_val = a.get("endDate")
        if div is not None and dt_val:
            dt = pd.to_datetime(dt_val, unit='ms') if isinstance(dt_val, (int, float)) else pd.to_datetime(dt_val)
            if prices is not None and not prices.empty:
                idx = prices.index.get_indexer([dt], method='nearest')[0]
                px_at_date = float(prices.iloc[idx]["Close"]) if idx >= 0 else price
                div_yield_vals.append(div / px_at_date * 100)
    div_yield_5y_avg = sum(div_yield_vals) / len(div_yield_vals) if div_yield_vals else 0.0
    
    def _calc_fcf_ps(fcf, sh):
        if not fcf or not sh or sh <= 0:
            return None
        val = fcf / sh
        if val > 500:
            val = fcf / (sh * 1_000_000.0)
        elif val > 50:
            val = fcf / (sh * 1_000.0)
        return round(val, 2) if (val and val > 0 and val < 500) else None

    pcf_vals = []
    for a in last_5_annuals:
        fcf = a.get("fcf")
        sh = a.get("sharesOut")
        dt_val = a.get("endDate")
        fcf_ps = _calc_fcf_ps(fcf, sh)
        if fcf_ps and dt_val:
            dt = pd.to_datetime(dt_val, unit='ms') if isinstance(dt_val, (int, float)) else pd.to_datetime(dt_val)
            if prices is not None and not prices.empty and fcf_ps > 0:
                idx = prices.index.get_indexer([dt], method='nearest')[0]
                px_at_date = float(prices.iloc[idx]["Close"]) if idx >= 0 else price
                pcf_vals.append(px_at_date / fcf_ps)
    pcf_5y_avg = sum(pcf_vals) / len(pcf_vals) if pcf_vals else None

    pe_ttm = M._f(info.get("trailingPE"))
    pb_ttm = M._f(info.get("priceToBook"))
    ps_ttm = M._f(info.get("priceToSalesTrailing12Months")) or M._f(info.get("priceToSales"))
    
    # P/CF actual: TTM computado de estados de flujos (única fuente de verdad,
    # consistente con el último punto de la serie histórica del chart). Fallback
    # al FCF de Yahoo y, en último caso, al último FCF anual.
    if fcf_ttm_now and mc_now and fcf_ttm_now > 0:
        pcf_ttm = round(mc_now / fcf_ttm_now, 2)
    else:
        fcf_now = annuals[-1].get("fcf") if annuals else None
        mc_fb = mc_now or M._f(info.get("marketCap"))
        fcf_yield = (fcf_now / mc_fb * 100) if (fcf_now and mc_fb) else None
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

    shares_now = M._f(info.get("sharesOutstanding"))
    fcf_ps_ttm = _calc_fcf_ps(fcf_now, shares_now) if (fcf_now and shares_now) else None
    
    fcf_ps_vals = []
    for a in last_5_annuals:
        fps = _calc_fcf_ps(a.get("fcf"), a.get("sharesOut"))
        if fps:
            fcf_ps_vals.append(fps)
    fcf_ps_5y_avg = round(sum(fcf_ps_vals) / len(fcf_ps_vals), 2) if fcf_ps_vals else None

    roc_ttm = V.greenblatt_roc(info, annuals)

    return {
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
        "grossMargin": {"val": (M._f(info.get("grossMargins")) * 100 if M._f(info.get("grossMargins")) else (annuals[-1].get("grossMargin") if annuals else None)), "sector": sec.get("grossMargin") or 40.0, "avg5y": gross_margin_5y},
        "opMargin": {"val": (M._f(info.get("operatingMargins")) * 100 if M._f(info.get("operatingMargins")) else (annuals[-1].get("opMargin") if annuals else None)), "sector": sec.get("opMargin") or 12.0, "avg5y": op_margin_5y},
        "roa": {"val": (M._f(info.get("returnOnAssets")) * 100 if M._f(info.get("returnOnAssets")) else (annuals[-1].get("netIncome") / annuals[-1].get("assets") * 100 if annuals and annuals[-1].get("netIncome") and annuals[-1].get("assets") else None)), "sector": sec.get("roa") or 8.0, "avg5y": roa_5y},
        "roc": {"val": roc_ttm, "sector": sec.get("roe") * 0.9 if sec.get("roe") else 15.0, "avg5y": roic_5y_avg},
        "roic10yAvg": roic_5y_avg,
        "revGrowth10y": cagr_10y("revenue"),
        "netIncomeGrowth10y": cagr_10y("netIncome"),
        "fcfGrowth10y": cagr_10y("fcf")
    }


def build_payload(symbol: str, refresh: bool = False):
    from .main import CACHE_VERSION
    key = f"stock_{CACHE_VERSION}_{symbol.upper().replace('/', '_')}"
    if not refresh:
        cached = cache_get(key)
        if cached:
            return cached

    # EDGAR se descarga en paralelo con Yahoo (ahorra varios segundos)
    with ThreadPoolExecutor(max_workers=1) as _ex:
        _edgar_fut = _ex.submit(E.get_annual_history, symbol)
        raw = RawData(symbol)
        edgar_hist = _edgar_fut.result()
    if not raw.is_valid():
        return None

    info = raw.info
    prices = raw.prices
    monthly = M.monthly_prices(prices)
    weekly = M.weekly_prices(prices)  # Para ratios más detallados
    price = M._f(info.get("currentPrice")) or float(prices["Close"].dropna().iloc[-1])

    # ------------------------------------------------ series históricas
    shares = M.shares_series(raw)

    eps_ttm = M.ttm_eps_series(raw)
    rev_ttm = M.ttm_from_statements(raw.inc_a, raw.inc_q, "Total Revenue", "Operating Revenue")
    equity = M.step_series(raw.bs_a, raw.bs_q, "Stockholders Equity", "Common Stock Equity")
    fcf_ttm = M.fcf_ttm_series(raw.cf_a, raw.cf_q)

    # EDGAR extiende la historia a 10-15+ años (solo empresas que reportan a la SEC).
    # Sus valores por acción vienen as-reported: hay que ajustarlos por splits
    # para que calcen con los precios ajustados de Yahoo.
    splits = M.splits_from_prices(prices)
    min_date = pd.Timestamp.now() - pd.DateOffset(years=MAX_HISTORY_YEARS)

    def _cut(s):
        return s[s.index >= min_date] if s is not None else None

    edgar_eps = M.split_adjust(E.to_series(edgar_hist, "eps"), splits, "per_share")
    edgar_shares = M.split_adjust(E.to_series(edgar_hist, "shares"), splits, "shares")

    eps_ttm = _cut(M.merge_series(eps_ttm, edgar_eps))
    rev_ttm = _cut(M.merge_series(rev_ttm, E.to_series(edgar_hist, "revenue")))
    equity = _cut(M.merge_series(equity, E.to_series(edgar_hist, "equity")))
    shares = _cut(M.merge_series(shares, edgar_shares))
    fcf_ttm = _cut(fcf_ttm)

    # Sanear trailingPE/trailingEps de Yahoo ante datos corruptos comparando con el EPS TTM auditado
    eps_ttm_computed = None
    if eps_ttm is not None and len(eps_ttm):
        try:
            eps_ttm_computed = float(eps_ttm.iloc[-1])
        except (TypeError, ValueError):
            pass

    cur_pe = M._f(info.get("trailingPE"))
    if eps_ttm_computed and eps_ttm_computed > 0 and price and price > 0:
        pe_computed = price / eps_ttm_computed
        if cur_pe is None or abs(cur_pe - pe_computed) / max(pe_computed, 1e-4) > 0.20:
            if cur_pe is not None:
                info["_peRawOriginal"] = cur_pe
                info["_peSanitized"] = True
            cur_pe = round(pe_computed, 2)
            info["trailingPE"] = cur_pe
            info["trailingEps"] = round(eps_ttm_computed, 2)

    # Usar precios semanales para charts más detallados
    pe_hist = M.ratio_history(weekly, eps_ttm, "per_share")
    if pe_hist is not None:
        # PE > 200 no es una señal de valoración: utilidad casi nula distorsiona
        pe_hist = pe_hist[pe_hist <= 200]
    ps_hist = M.ratio_history(weekly, rev_ttm, "total", shares)
    pb_hist = M.ratio_history(weekly, equity, "total", shares)
    pcf_hist = M.ratio_history(weekly, fcf_ttm, "total", shares)
    if pcf_hist is not None:
        pcf_hist = pcf_hist[pcf_hist <= 500]  # Filtrar valores extremos

    cur_ps = M._f(info.get("priceToSalesTrailing12Months")) or M._f(info.get("priceToSales"))
    cur_pb = M._f(info.get("priceToBook"))
    # FCF TTM de referencia: el computado de estados de flujos (misma serie que
    # alimenta el chart) y, si no hay, el de Yahoo. Fuente única de la verdad.
    fcf_t_now = None
    if fcf_ttm is not None and len(fcf_ttm):
        try:
            fcf_t_now = float(fcf_ttm.iloc[-1])
        except (TypeError, ValueError):
            pass
    if fcf_t_now is None or fcf_t_now <= 0:
        fcf_t_now = M._f(info.get("freeCashflow"))
    mc_px = M._f(info.get("marketCap"))
    cur_pcf = None
    if fcf_t_now and mc_px and fcf_t_now > 0:
        cur_pcf = round(mc_px / fcf_t_now, 2)

    def _snap_tail(pairs, cur_val):
        """Ancla el último punto válido de la serie al valor actual canónico
        (Yahoo/actual) para que todas las secciones muestren el mismo "hoy"."""
        if cur_val is None or cur_val <= 0 or not pairs:
            return pairs
        i = len(pairs) - 1
        while i >= 0 and pairs[i][1] is None:
            i -= 1
        if i < 0:
            return pairs
        pairs[i][1] = round(cur_val, 2)
        return pairs
    pe_pairs = _snap_tail(M._pairs(pe_hist, 2), cur_pe) if pe_hist is not None else []
    ps_pairs = _snap_tail(M._pairs(ps_hist, 2), cur_ps) if ps_hist is not None else []
    pb_pairs = _snap_tail(M._pairs(pb_hist, 2), cur_pb) if pb_hist is not None else []
    pcf_pairs = _snap_tail(M._pairs(pcf_hist, 2), cur_pcf) if pcf_hist is not None else []
    pe_stats = M.series_stats(pe_pairs)
    pcf_stats = M.series_stats(pcf_pairs)

    # series TTM para el overlay interactivo (precio vs fundamentales)
    ni_ttm = M.ttm_from_statements(raw.inc_a, raw.inc_q, "Net Income", "Net Income Common Stockholders")
    net_margin_ttm_series = None
    if rev_ttm is not None and ni_ttm is not None and len(rev_ttm) and len(ni_ttm):
        _idx = rev_ttm.index.union(ni_ttm.index).sort_values()
        _rev_r = rev_ttm.reindex(_idx).ffill()
        _ni_r = ni_ttm.reindex(_idx).ffill()
        _m = (_ni_r / _rev_r * 100)
        _m = _m[_m.notna()]
        if len(_m):
            net_margin_ttm_series = _m

    price_10y = prices["Close"][prices.index >= min_date].dropna()

    annuals = _merge_annuals(M.annual_fundamentals(raw), E.to_annual_rows(edgar_hist),
                             raw.dividends, splits)
    quarterlies = M.quarterly_fundamentals(raw)

    # ------------------------------------------------ snapshot actual
    # FCF TTM único (computado o fallback Yahoo), usado en fcfYield, P/CF del
    # grid de ratios y ancla del chart — un solo número en toda la app.
    fcf_now = fcf_t_now
    mc = mc_px

    sma50 = None
    sma200 = None
    rsi = None
    closes = prices["Close"].dropna()
    if len(closes) >= 50:
        sma50 = float(closes.rolling(50).mean().iloc[-1])
    if len(closes) >= 200:
        sma200 = float(closes.rolling(200).mean().iloc[-1])
    if len(closes) >= 15:
        delta = closes.diff()
        gain = delta.where(delta > 0, 0.0).ewm(alpha=1/14, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0.0)).ewm(alpha=1/14, adjust=False).mean()
        rs = gain / loss
        rsi_series = 100 - (100 / (1 + rs))
        rval = float(rsi_series.iloc[-1])
        rsi = round(rval, 1) if pd.notna(rval) and np.isfinite(rval) else None
    perf_1m = None
    perf_1y = None
    perf_ytd = None
    if len(closes) > 0:
        last_px = float(closes.iloc[-1])
        try:
            closes_naive = closes.tz_localize(None) if closes.index.tz is not None else closes
            # 1 mes
            m1_date = closes_naive.index[-1] - pd.DateOffset(months=1)
            m1_idx = closes_naive.index.get_indexer([m1_date], method='nearest')[0]
            if m1_idx >= 0:
                perf_1m = round((last_px / float(closes_naive.iloc[m1_idx]) - 1) * 100, 2)
            # 1 año
            y1_date = closes_naive.index[-1] - pd.DateOffset(years=1)
            y1_idx = closes_naive.index.get_indexer([y1_date], method='nearest')[0]
            if y1_idx >= 0:
                perf_1y = round((last_px / float(closes_naive.iloc[y1_idx]) - 1) * 100, 2)
            # YTD
            ytd_date = pd.Timestamp(year=closes_naive.index[-1].year - 1, month=12, day=31)
            ytd_idx = closes_naive.index.get_indexer([ytd_date], method='nearest')[0]
            if ytd_idx >= 0:
                perf_ytd = round((last_px / float(closes_naive.iloc[ytd_idx]) - 1) * 100, 2)
        except Exception:
            pass

    f_score = V.piotroski_f_score(annuals)
    roc = V.greenblatt_roc(info, annuals)

    payout_val = M._f(info.get("payoutRatio"))
    if payout_val is None and annuals:
        last_a = annuals[-1]
        if last_a.get("dividendPS") is not None and last_a.get("eps") is not None and last_a["eps"] > 0:

            payout_val = last_a["dividendPS"] / last_a["eps"]

    roe_val = M._f(info.get("returnOnEquity"))
    if roe_val is None and annuals and annuals[-1].get("roe") is not None:
        roe_val = annuals[-1]["roe"] / 100.0 if annuals[-1]["roe"] > 1.0 else annuals[-1]["roe"]

    roa_val = M._f(info.get("returnOnAssets"))
    if roa_val is None and annuals and annuals[-1].get("netIncome") and annuals[-1].get("assets"):
        roa_val = annuals[-1]["netIncome"] / annuals[-1]["assets"]

    gm_val = M._f(info.get("grossMargins"))
    if gm_val is None and annuals and annuals[-1].get("grossMargin") is not None:
        gm_val = annuals[-1]["grossMargin"] / 100.0 if annuals[-1]["grossMargin"] > 1.0 else annuals[-1]["grossMargin"]

    om_val = M._f(info.get("operatingMargins"))
    if om_val is None and annuals and annuals[-1].get("opMargin") is not None:
        om_val = annuals[-1]["opMargin"] / 100.0 if annuals[-1]["opMargin"] > 1.0 else annuals[-1]["opMargin"]

    nm_val = M._f(info.get("profitMargins"))
    if nm_val is None and annuals and annuals[-1].get("netMargin") is not None:
        nm_val = annuals[-1]["netMargin"] / 100.0 if annuals[-1]["netMargin"] > 1.0 else annuals[-1]["netMargin"]

    fpe_val = M._f(info.get("forwardPE"))
    if fpe_val is None and price and info.get("forwardEps") and info["forwardEps"] > 0:
        fpe_val = price / info["forwardEps"]
        
    div_yield_ttm = M._f(info.get("trailingAnnualDividendYield"))
    if div_yield_ttm is not None:
        div_yield_ttm *= 100
    else:
        div_yield_ttm = M._f(info.get("dividendYield"))
        if div_yield_ttm is not None:
            div_yield_ttm *= 100
        elif info.get("dividendRate") and price:
            div_yield_ttm = float(info["dividendRate"]) / price * 100
    if div_yield_ttm is None:
        div_yield_ttm = 0.0

    # Trailing PE: prefer direct field, else compute from EPS and price
    tpe_val = M._f(info.get("trailingPE"))
    if tpe_val is None and price and info.get("trailingEps") and info["trailingEps"] > 0:
        tpe_val = round(price / info["trailingEps"], 2)

    current = {
        "pe": tpe_val,
        "trailingPE": tpe_val,
        "forwardPe": fpe_val,
        "forwardPE": fpe_val,
        "ps": M._f(info.get("priceToSalesTrailing12Months")),
        "pb": M._f(info.get("priceToBook")),
        "evEbitda": M._f(info.get("enterpriseToEbitda")),
        "evRevenue": M._f(info.get("enterpriseToRevenue")),
        "peg": M._f(info.get("trailingPegRatio") or info.get("pegRatio")),
        "divYield": div_yield_ttm,
        "payout": payout_val,
        "roe": roe_val,
        "roa": roa_val,
        "grossMargin": gm_val,
        "opMargin": om_val,
        "netMargin": nm_val,
        "debtToEquity": M._f(info.get("debtToEquity")),
        "currentRatio": M._f(info.get("currentRatio")),
        "quickRatio": M._f(info.get("quickRatio")),
        "beta": M._f(info.get("beta")),
        "eps": M._f(info.get("trailingEps")),
        "epsForward": M._f(info.get("forwardEps")),
        # bvps: Yahoo sometimes returns null — fallback to equity/shares from latest annual
        "bvps": (M._f(info.get("bookValue"))
                 or (annuals[-1].get("equity") / annuals[-1].get("sharesOut")
                     if annuals and annuals[-1].get("equity") and annuals[-1].get("sharesOut") and annuals[-1]["sharesOut"] > 0
                     else None)),

        "revenueGrowth": M._f(info.get("revenueGrowth")),
        "earningsGrowth": M._f(info.get("earningsGrowth")),
        "fcf": fcf_now,
        "fcfYield": (fcf_now / mc * 100) if (fcf_now and mc) else None,
        # totalCash/Debt: fallback from latest annual when Yahoo returns null
        "totalCash": (M._f(info.get("totalCash"))
                      or (annuals[-1].get("cash") if annuals else None)),
        "totalDebt": (M._f(info.get("totalDebt"))
                      or (annuals[-1].get("totalDebt") if annuals else None)),
        "workingCapital": annuals[-1].get("workingCapital") if annuals else None,
        "sma50": round(sma50, 2) if sma50 else None,
        "sma200": round(sma200, 2) if sma200 else None,
        "rsi": rsi,
        "fScore": f_score,
        "roc": round(roc, 1) if roc else None,
        "perf1m": perf_1m,
        "perf1y": perf_1y,
        "perfYtd": perf_ytd,
        "analystTarget": M._f(info.get("targetMeanPrice")),
        "analystRecommendation": info.get("recommendationKey"),
        "insiderPercent": (M._f(info.get("heldPercentInsiders")) * 100
                           if M._f(info.get("heldPercentInsiders")) is not None
                           else None),
        "shortPercent": (M._f(info.get("shortPercentOfFloat")) * 100
                         if M._f(info.get("shortPercentOfFloat")) is not None
                         else None),
        "shortRatio": M._f(info.get("shortRatio")),
    }

    altman_z = None
    try:
        last_a = annuals[-1] if annuals else {}
        assets_val = last_a.get("assets")
        eq_val = last_a.get("equity")
        wc_val = current.get("workingCapital")
        debt_val = current.get("totalDebt")
        sales_val = last_a.get("revenue")
        ni_val = last_a.get("netIncome")
        op_val = last_a.get("opMargin")
        ebit_val = (sales_val * op_val / 100) if (sales_val and op_val) else ni_val

        if assets_val and assets_val > 0:
            x1 = (wc_val / assets_val) if wc_val else 0.2
            x2 = (eq_val * 0.5 / assets_val) if eq_val else 0.15
            x3 = (ebit_val / assets_val) if ebit_val else 0.15
            x4 = (eq_val / debt_val) if (eq_val and debt_val and debt_val > 0) else 1.0
            x5 = (sales_val / assets_val) if sales_val else 0.8
            altman_z = round(1.2 * x1 + 1.4 * x2 + 3.3 * x3 + 0.6 * x4 + 0.99 * x5, 2)
    except Exception:
        pass

    current["altmanZ"] = altman_z


    bond10y = bond_yield_10y()
    fmp_rows = F.fetch_analyst_estimates(symbol)
    valuation = V.build_valuation(price, info, annuals, pe_stats, bond10y, fmp_rows=fmp_rows)
    scorecard = V.buffett_scorecard(info, annuals, pe_stats, pe_pairs=pe_pairs, price=price)
    next_earnings, next_earnings_est, sec_filings = _sec_context(symbol, raw.calendar)

    dividends_annual = M.dividend_history(raw, prices=prices)
    div_safety = _dividend_safety(annuals, dividends_annual, info)
    warnings = Q.build_warnings(info, annuals, valuation, pe_pairs, edgar_hist)

    # foto del día para el historial de margen de seguridad
    S.append(symbol, price, valuation["marginOfSafety"], valuation["consensus"])

    ratios = calculate_ratios_payload(price, info, annuals, prices, pe_hist, pb_hist, ps_hist,
                                      fcf_ttm_now=fcf_now, mc_now=mc)
    estimates = build_estimates_payload(raw, info, annuals, price, symbol=symbol, fmp_rows=fmp_rows)
    insiders_holders = build_insiders_holders_payload(raw, info)

    payload = {
        "symbol": symbol.upper(),
        "profile": {
            "name": info.get("longName") or info.get("shortName") or symbol.upper(),
            "sector": info.get("sector") or ("Servicios Financieros / Chile" if symbol.upper().endswith(".SN") else None),
            "industry": info.get("industry"),
            "country": info.get("country") or ("Chile" if symbol.upper().endswith(".SN") else None),
            "website": info.get("website"),
            "employees": info.get("fullTimeEmployees") or info.get("employees"),
            "summary": (info.get("longBusinessSummary") or info.get("description") or info.get("summary") or "")[:600],
            "exchange": info.get("fullExchangeName") or info.get("exchange"),
            "currency": info.get("currency") or ("CLP" if symbol.upper().endswith(".SN") else "USD"),
            "nextEarnings": next_earnings,
            "nextEarningsEst": next_earnings_est,
            "secFilings": sec_filings,
        },
        "quote": {
            "price": price,
            "previousClose": M._f(info.get("previousClose")),
            "marketCap": mc,
            "high52w": M._f(info.get("fiftyTwoWeekHigh")),
            "low52w": M._f(info.get("fiftyTwoWeekLow")),
            "volume": (M._f(info.get("volume")) or M._f(info.get("regularMarketVolume"))
                       or (int(prices["Volume"].dropna().iloc[-1]) if prices is not None and "Volume" in prices.columns and not prices["Volume"].dropna().empty else None)),
            "avgVolume": (M._f(info.get("averageVolume")) or M._f(info.get("averageVolume10days"))
                         or (int(prices["Volume"].dropna().tail(30).mean()) if prices is not None and "Volume" in prices.columns and not prices["Volume"].dropna().empty else None)),
            "postMarketPrice": M._f(info.get("postMarketPrice")),
            "postMarketChangePercent": M._f(info.get("postMarketChangePercent")),
        },
        "current": current,
        "history": {
            "price": [[M._ts(i), round(float(v), 2)] for i, v in price_10y.items()],
            "peTtm": pe_pairs,
            "psTtm": ps_pairs,
            "pbTtm": pb_pairs,
            "pcfTtm": pcf_pairs,
            "peStats": pe_stats,
            "psStats": M.series_stats(ps_pairs),
            "pbStats": M.series_stats(pb_pairs),
            "pcfStats": pcf_stats,
            "epsTtm": M._pairs(eps_ttm, 2) if eps_ttm is not None else [],
            "revTtm": M._pairs(rev_ttm, 0) if rev_ttm is not None else [],
            "netMarginTtm": M._pairs(net_margin_ttm_series, 2) if net_margin_ttm_series is not None else [],
            "shares": M._pairs(shares.resample("QE").last().dropna(), 0) if shares is not None else [],
            "dividends": dividends_annual,
            "mos": S.history(symbol),
        },
        "annuals": annuals,
        "quarterlies": quarterlies,
        "provider": getattr(raw, "provider", "Financial Modeling Prep (FMP)"),
        "isFallback": getattr(raw, "is_fallback", False) if hasattr(raw, "is_fallback") else False,
        "news": raw.news if hasattr(raw, "news") else None,

        "growthTable": _growth_table(annuals),
        "valuation": valuation,
        "scorecard": scorecard,
        "dividendSafety": div_safety,
        "warnings": warnings,
        "ratios": ratios,
        "estimates": estimates,
        "insidersHolders": insiders_holders,
        "earningsSurprises": _build_earnings_surprises(getattr(raw, "earnings_dates", None)),
    }
    payload = jclean(payload)
    cache_set(key, payload)
    return payload


def _build_insiders_holders_payload(raw, info):
    """Extrae transacciones de insiders y principales fondos institucionales."""
    insiders = []
    try:
        if hasattr(raw, "insider_transactions") and raw.insider_transactions is not None and not raw.insider_transactions.empty:
            df = raw.insider_transactions.head(10)
            for _, row in df.iterrows():
                d_str = ""
                if "Start Date" in row and row["Start Date"] is not None:
                    d_str = str(row["Start Date"])[:10]
                insiders.append({
                    "insider": str(row.get("Insider", "—")),
                    "position": str(row.get("Position", "—")),
                    "transaction": str(row.get("Transaction", row.get("Text", "—"))),
                    "shares": M._f(row.get("Shares")),
                    "value": M._f(row.get("Value")),
                    "date": d_str,
                })
    except Exception:
        pass

    holders = []
    try:
        if hasattr(raw, "institutional_holders") and raw.institutional_holders is not None and not raw.institutional_holders.empty:
            df = raw.institutional_holders.head(10)
            for _, row in df.iterrows():
                d_str = ""
                if "Date Reported" in row and row["Date Reported"] is not None:
                    d_str = str(row["Date Reported"])[:10]
                holders.append({
                    "holder": str(row.get("Holder", "—")),
                    "shares": M._f(row.get("Shares")),
                    "value": M._f(row.get("Value")),
                    "pctChange": M._f(row.get("pctChange")),
                    "date": d_str,
                })
    except Exception:
        pass

    return {
        "insiders": insiders,
        "holders": holders,
        "insiderPercent": M._f(info.get("heldPercentInsiders")) * 100 if info.get("heldPercentInsiders") is not None else None,
        "institutionPercent": M._f(info.get("heldPercentInstitutions")) * 100 if info.get("heldPercentInstitutions") is not None else None,
    }
