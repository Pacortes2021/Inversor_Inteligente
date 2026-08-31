"""Cálculo de métricas, series históricas de ratios y fundamentales anuales."""

import math

import numpy as np
import pandas as pd

from .data import RawData


# ---------------------------------------------------------------- utilidades

def _f(x):
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def _row(df, *names):
    """Primera fila existente entre varios nombres posibles de línea contable."""
    if df is None:
        return None
    for n in names:
        if n in df.index:
            s = df.loc[n].dropna()
            if not s.empty:
                s.index = pd.to_datetime(s.index).tz_localize(None)
                return s.sort_index()
    return None


def _g(df, col, *names):
    """Valor de una línea contable en una columna (fecha) puntual."""
    if df is None:
        return None
    for n in names:
        if n in df.index and col in df.columns:
            v = df.loc[n, col]
            out = _f(v)
            if out is not None:
                return out
    return None


def _ts(x) -> int:
    return int(pd.Timestamp(x).timestamp() * 1000)


def _pairs(series, ndigits=3):
    return [[_ts(i), round(float(v), ndigits)] for i, v in series.items() if _f(v) is not None]


# ------------------------------------------------------- series TTM y ratios

def ttm_from_statements(df_a, df_q, *names):
    """Serie TTM combinando cierres anuales y suma móvil de 4 trimestres."""
    pts = {}
    s_a = _row(df_a, *names)
    if s_a is not None:
        for dt, v in s_a.items():
            if _f(v) is not None:
                pts[pd.Timestamp(dt)] = float(v)
    s_q = _row(df_q, *names)
    if s_q is not None and len(s_q) >= 4:
        roll = s_q.rolling(4, min_periods=4).sum().dropna()
        for dt, v in roll.items():
            if _f(v) is not None:
                pts[pd.Timestamp(dt)] = float(v)
    if not pts:
        return None
    return pd.Series(pts).sort_index()


def ttm_eps_series(raw: "RawData"):
    """Serie TTM de EPS diluido, imputando los trimestres sin EPS (NaN) con
    NI_del_trimestre / acciones_del_cierre (mismo criterio de Yahoo). Evita
    que un hueco de datos de yfinance (frecuente en tickers CL) rompa o
    subestime el EPS trailing 12m."""
    pts = {}
    s_a = _row(raw.inc_a, "Diluted EPS", "Basic EPS")
    if s_a is not None:
        for dt, v in s_a.items():
            if _f(v) is not None:
                pts[pd.Timestamp(dt)] = float(v)

    q = raw.inc_q
    if q is not None and len(q.columns) >= 4:
        s_q = _row(q, "Diluted EPS", "Basic EPS")
        ni = _row(q, "Net Income", "Net Income Common Stockholders")
        sh = _qb_series(raw, "Ordinary Shares Number", "Share Issued")
        qpts = {}
        for dt in pd.to_datetime(q.columns, errors="coerce"):
            if pd.isna(dt):
                continue
            v = _f(s_q.get(dt)) if s_q is not None else None
            if ni is not None and dt in ni.index:
                nv = _f(ni.loc[dt])
                sv = _f(sh.loc[dt]) if sh is not None and dt in sh.index else None
                if nv is not None and sv is not None and sv > 0:
                    implied = nv / sv
                    if v is None or abs(v - implied) / max(abs(implied), 1e-4) > 0.25:
                        v = implied
            if v is not None:
                qpts[dt] = float(v)
        if len(qpts) >= 4:
            roll = pd.Series(qpts).sort_index().rolling(4, min_periods=4).sum().dropna()
            for dt, vq in roll.items():
                if _f(vq) is not None:
                    pts[pd.Timestamp(dt)] = float(vq)

    if not pts:
        return None
    return pd.Series(pts).sort_index()


def _qb_series(raw: "RawData", *names):
    """Serie de acciones desde el balance (trimestral) para imputación."""
    for df in (getattr(raw, "bs_q", None), getattr(raw, "bs_a", None)):
        if df is None:
            continue
        for n in names:
            if n in df.index:
                s = df.loc[n].dropna()
                if not s.empty:
                    s.index = pd.to_datetime(s.index).tz_localize(None)
                    return s.sort_index()
    return None


def fcf_ttm_series(cf_a, cf_q):
    """Serie TTM de Free Cash Flow desde estados de flujos de caja."""
    pts = {}
    # Anuales
    if cf_a is not None:
        for col in cf_a.columns:
            ocf = _f(cf_a.loc["Operating Cash Flow", col]) if "Operating Cash Flow" in cf_a.index else None
            capex = _f(cf_a.loc["Capital Expenditure", col]) if "Capital Expenditure" in cf_a.index else None
            fcf = _f(cf_a.loc["Free Cash Flow", col]) if "Free Cash Flow" in cf_a.index else None
            if fcf is None and ocf is not None and capex is not None:
                fcf = ocf + capex
            if fcf is not None:
                pts[pd.Timestamp(col)] = float(fcf)
    # Trimestrales (TTM)
    if cf_q is not None and len(cf_q.columns) >= 4:
        for i in range(3, len(cf_q.columns)):
            cols = cf_q.columns[i-3:i+1]
            ocf_sum = sum(_f(cf_q.loc["Operating Cash Flow", c]) or 0 for c in cols if "Operating Cash Flow" in cf_q.index)
            capex_sum = sum(_f(cf_q.loc["Capital Expenditure", c]) or 0 for c in cols if "Capital Expenditure" in cf_q.index)
            fcf_sum = sum(_f(cf_q.loc["Free Cash Flow", c]) or 0 for c in cols if "Free Cash Flow" in cf_q.index)
            if fcf_sum == 0 and ocf_sum != 0:
                fcf_sum = ocf_sum + capex_sum
            if fcf_sum != 0:
                pts[pd.Timestamp(cf_q.columns[i])] = float(fcf_sum)
    if not pts:
        return None
    return pd.Series(pts).sort_index()


def step_series(df_a, df_q, *names):
    """Serie de saldos (balance): valor puntual en cada cierre disponible."""
    pts = {}
    for df in (df_a, df_q):
        s = _row(df, *names)
        if s is not None:
            for dt, v in s.items():
                if _f(v) is not None:
                    pts[pd.Timestamp(dt)] = float(v)
    if not pts:
        return None
    return pd.Series(pts).sort_index()


def splits_from_prices(prices: pd.DataFrame):
    """Serie de splits (fecha → ratio) extraída del historial de precios."""
    if prices is None or "Stock Splits" not in prices.columns:
        return None
    s = prices["Stock Splits"]
    s = s[s > 0]
    return s if not s.empty else None


def split_adjust(series: pd.Series, splits: pd.Series, mode: str = "per_share"):
    """Lleva valores históricos as-reported a la base accionaria actual.
    Para cada punto, factor = producto de splits posteriores a esa fecha.
    mode 'per_share' (EPS, DPS): divide. mode 'shares': multiplica."""
    if series is None or series.empty or splits is None or splits.empty:
        return series
    out = {}
    for dt, v in series.items():
        factor = float(splits[splits.index > dt].prod()) or 1.0
        out[dt] = v / factor if mode == "per_share" else v * factor
    return pd.Series(out).sort_index()


def split_factor(splits: pd.Series, ts) -> float:
    """Factor acumulado de splits posteriores a una fecha."""
    if splits is None or splits.empty:
        return 1.0
    return float(splits[splits.index > pd.Timestamp(ts)].prod()) or 1.0


def merge_series(primary: pd.Series, extra: pd.Series):
    """Combina dos series temporales; ante fechas duplicadas gana `primary`."""
    if extra is None or extra.empty:
        return primary
    if primary is None or primary.empty:
        return extra
    comb = pd.concat([extra, primary])
    comb = comb[~comb.index.duplicated(keep="last")]
    return comb.sort_index()


def monthly_prices(prices: pd.DataFrame) -> pd.Series:
    m = prices["Close"].resample("ME").last().dropna()
    # incluye el precio más reciente como último punto
    last = prices["Close"].dropna()
    if not last.empty:
        m = pd.concat([m, last.iloc[[-1]]])
        m = m[~m.index.duplicated(keep="last")].sort_index()
    return m


def weekly_prices(prices: pd.DataFrame) -> pd.Series:
    """Precios semanales para charts más detallados."""
    w = prices["Close"].resample("W").last().dropna()
    last = prices["Close"].dropna()
    if not last.empty:
        w = pd.concat([w, last.iloc[[-1]]])
        w = w[~w.index.duplicated(keep="last")].sort_index()
    return w


def ratio_history(monthly: pd.Series, fundamental: pd.Series, kind: str,
                  shares: pd.Series = None, min_den: float = 1e-9):
    """Ratio precio/fundamental mensual. kind: 'per_share' (denominador ya es
    por acción) o 'total' (denominador total, requiere serie de acciones)."""
    if fundamental is None or fundamental.empty:
        return None
    start = fundamental.index.min() - pd.Timedelta(days=45)
    m = monthly[monthly.index >= start]
    if m.empty:
        return None
    idx = m.index.union(fundamental.index).sort_values()
    fund = fundamental.reindex(idx).ffill().reindex(m.index)

    if kind == "total":
        if shares is None or shares.empty:
            return None
        sh = shares.reindex(idx.union(shares.index).sort_values()).ffill().reindex(m.index)
        den = fund / sh
    else:
        den = fund

    ratio = m / den
    ratio = ratio[(den > min_den) & np.isfinite(ratio)]
    ratio = ratio[ratio > 0]
    return ratio.dropna() if not ratio.empty else None


def series_stats(pairs):
    if not pairs:
        return None
    vals = np.array([p[1] for p in pairs], dtype=float)
    cur = float(vals[-1])
    med = float(np.median(vals))
    return {
        "current": round(cur, 2),
        "median": round(med, 2),
        "mean": round(float(vals.mean()), 2),
        "std": round(float(vals.std()), 2),
        "p25": round(float(np.percentile(vals, 25)), 2),
        "p75": round(float(np.percentile(vals, 75)), 2),
        "min": round(float(vals.min()), 2),
        "max": round(float(vals.max()), 2),
        "vsMedian": round((cur - med) / abs(med) * 100, 1) if med else None,
    }


# ------------------------------------------------------ fundamentales anuales

def build_fundamentals(inc, bs, cf, dividends=None):
    if inc is None:
        return []

    div_by_year = {}
    if dividends is not None and not dividends.empty:
        div_by_year = dividends.groupby(dividends.index.year).sum().to_dict()

    out = []
    for col in sorted(inc.columns):
        col_bs = _closest_col(bs, col)
        col_cf = _closest_col(cf, col)

        rev = _g(inc, col, "Total Revenue", "Operating Revenue")
        ni = _g(inc, col, "Net Income", "Net Income Common Stockholders")
        gp = _g(inc, col, "Gross Profit")
        op = _g(inc, col, "Operating Income", "EBIT")
        ebit = _g(inc, col, "EBIT", "Operating Income")
        ebitda = _g(inc, col, "EBITDA", "Normalized EBITDA")
        eps = _g(inc, col, "Diluted EPS", "Basic EPS")
        pretax = _g(inc, col, "Pretax Income")
        tax = _g(inc, col, "Tax Provision")
        interest = _g(inc, col, "Interest Expense")

        equity = _g(bs, col_bs, "Stockholders Equity", "Common Stock Equity", "Total Equity Gross Minority Interest")
        debt = _g(bs, col_bs, "Total Debt")
        cash = _g(bs, col_bs, "Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments")
        cur_assets = _g(bs, col_bs, "Current Assets")
        cur_liab = _g(bs, col_bs, "Current Liabilities")
        assets = _g(bs, col_bs, "Total Assets")
        long_term_debt = _g(bs, col_bs, "Long Term Debt", "Long Term Debt And Capital Lease Obligation")
        shares_n = _g(bs, col_bs, "Ordinary Shares Number", "Share Issued")

        ocf = _g(cf, col_cf, "Operating Cash Flow")
        capex = _g(cf, col_cf, "Capital Expenditure")
        fcf = _g(cf, col_cf, "Free Cash Flow")
        if fcf is None and ocf is not None and capex is not None:
            fcf = (ocf - abs(capex)) if capex > 0 else (ocf + capex)

        tax_rate = (tax / pretax) if (tax is not None and pretax and pretax > 0) else 0.21
        tax_rate = min(max(tax_rate, 0.0), 0.5)
        invested = None
        if equity is not None:
            invested = equity + (debt or 0) - (cash or 0)
        roic = (ebit * (1 - tax_rate) / invested * 100) if (ebit is not None and invested and invested > 0) else None

        year = pd.Timestamp(col).year
        month = pd.Timestamp(col).month
        quarter = (month - 1) // 3 + 1  # 1-4 based on month
        out.append({
            "year": year,
            "quarter": quarter,
            "endDate": _ts(col),
            "revenue": rev, "netIncome": ni, "eps": eps,
            "grossMargin": (gp / rev * 100) if (gp is not None and rev) else None,
            "opMargin": (op / rev * 100) if (op is not None and rev) else None,
            "netMargin": (ni / rev * 100) if (ni is not None and rev) else None,
            "ocf": ocf, "capex": capex, "fcf": fcf,
            "fcfMargin": (fcf / rev * 100) if (fcf is not None and rev) else None,
            "equity": equity, "totalDebt": debt, "cash": cash,
            "debtToEquity": (debt / equity) if (debt is not None and equity and equity > 0) else None,
            "currentRatio": (cur_assets / cur_liab) if (cur_assets is not None and cur_liab) else None,
            "roe": (ni / equity * 100) if (ni is not None and equity and equity > 0) else None,
            "roic": roic,
            "interestCoverage": (ebit / abs(interest)) if (ebit is not None and interest) else None,
            "ebitda": ebitda,
            "debtToEbitda": (debt / ebitda) if (debt is not None and ebitda and ebitda > 0) else None,
            "assets": assets,
            "workingCapital": (cur_assets - cur_liab) if (cur_assets is not None and cur_liab is not None) else None,
            "longTermDebt": long_term_debt,
            "shares": shares_n,
            "sharesOut": shares_n,
            "dividendPS": div_by_year.get(year, 0.0) if dividends is not None else 0.0
        })
    return out

def annual_fundamentals(raw: RawData):
    return build_fundamentals(raw.inc_a, raw.bs_a, raw.cf_a, raw.dividends)

def quarterly_fundamentals(raw: RawData):
    return build_fundamentals(raw.inc_q, raw.bs_q, raw.cf_q, None)


def _closest_col(df, target):
    """Columna de df con fecha más cercana a target (mismo año fiscal)."""
    if df is None or not len(df.columns):
        return None
    target = pd.Timestamp(target)
    cols = [pd.Timestamp(c) for c in df.columns]
    best = min(cols, key=lambda c: abs((c - target).days))
    if abs((best - target).days) > 180:
        return None
    for c in df.columns:
        if pd.Timestamp(c) == best:
            return c
    return None


# ------------------------------------------------------------- serie acciones

def shares_series(raw: RawData):
    """Serie de acciones en circulación (para PS/PB y gráfico de recompras)."""
    if raw.shares is not None and not raw.shares.empty:
        s = raw.shares.astype(float)
        return s.resample("ME").last().dropna()
    s = step_series(raw.bs_a, raw.bs_q, "Ordinary Shares Number", "Share Issued")
    if s is not None:
        return s
    n = _f(raw.info.get("sharesOutstanding"))
    if n:
        idx = pd.date_range(end=pd.Timestamp.now(), periods=2, freq="YS")
        return pd.Series([n, n], index=idx)
    return None


# -------------------------------------------------------------- historia larga
# Dividendos anuales (historia larga de Yahoo)

def dividend_history(raw, prices=None, max_years=25):
    if raw.dividends is None or raw.dividends.empty:
        return []
    ann = raw.dividends.groupby(raw.dividends.index.year).sum()
    import pandas as pd
    cur_year = pd.Timestamp.now().year
    ann = ann[ann.index >= cur_year - max_years]
    
    res = []
    for y, v in ann.items():
        yld = None
        if prices is not None and not prices.empty:
            px_yr = prices[prices.index.year == y]["Close"]
            if not px_yr.empty:
                avg_px = float(px_yr.mean())
                if avg_px > 0:
                    yld = round(float(v) / avg_px * 100, 2)
        res.append([int(y), round(float(v), 4), yld])
    return res
