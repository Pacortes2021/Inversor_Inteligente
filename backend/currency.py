"""Política monetaria y conversión de datos financieros.

La moneda visible y de cálculo depende del mercado: los símbolos chilenos se
presentan en CLP y los estadounidenses en USD. Yahoo puede entregar estados de
una empresa chilena en USD aunque su acción cotice en CLP; en ese caso los
montos contables se convierten antes de compararlos con el precio.
"""

from __future__ import annotations

import copy
import math
import time

import pandas as pd

from .data import cache_get, cache_set, price_history


FX_TICKERS = {
    ("USD", "CLP"): ("CLP=X", "multiply"),  # CLP por un USD
    ("CLP", "USD"): ("CLP=X", "divide"),
}

# Campos de ``Ticker.info`` expresados en la moneda de los estados. Se dejan
# fuera precios, capitalización y dividendos, que Yahoo entrega en la moneda de
# cotización.
INFO_FINANCIAL_AMOUNTS = {
    "freeCashflow", "operatingCashflow", "totalCash", "totalDebt",
    "totalRevenue", "grossProfits", "ebitda", "netIncomeToCommon",
    "totalCurrentAssets", "totalCurrentLiabilities",
}

ANNUAL_FINANCIAL_AMOUNTS = {
    "revenue", "netIncome", "ocf", "capex", "fcf", "equity", "totalDebt",
    "cash", "ebitda", "assets", "totalLiabilities", "retainedEarnings",
    "workingCapital", "longTermDebt",
    "ebit", "interestExpense", "stockCompensation",
}

FMP_FINANCIAL_AMOUNTS = {
    "revenueAvg", "revenueLow", "revenueHigh", "ebitdaAvg", "ebitdaLow",
    "ebitdaHigh", "netIncomeAvg", "netIncomeLow", "netIncomeHigh",
    "epsAvg", "epsLow", "epsHigh",
}


def _number(value):
    return isinstance(value, (int, float)) and math.isfinite(value)


def market_currency(symbol: str, info: dict | None = None) -> str:
    """Moneda que ve el usuario y en la que se realizan los cálculos."""
    symbol = (symbol or "").upper().strip()
    if symbol.endswith(".SN"):
        return "CLP"
    currency = str((info or {}).get("currency") or "").upper()
    return currency or "USD"


def _fx_factor(source: str, target: str, raw_rate: float) -> float | None:
    pair = FX_TICKERS.get((source, target))
    if not pair or not _number(raw_rate) or raw_rate <= 0:
        return None
    return raw_rate if pair[1] == "multiply" else 1.0 / raw_rate


def current_fx_rate(source: str, target: str) -> dict | None:
    """Última tasa disponible con metadatos y caché de seis horas."""
    source, target = source.upper(), target.upper()
    if source == target:
        return {"rate": 1.0, "rawRate": 1.0, "ticker": None, "date": None}
    pair = FX_TICKERS.get((source, target))
    if not pair:
        return None
    ticker = pair[0]
    key = f"fx_current_{source}_{target}"
    cached = cache_get(key)
    if cached and _number(cached.get("rate")):
        return cached
    try:
        history = price_history(ticker, period="1mo", interval="1d")
        close = history["Close"].dropna() if history is not None and "Close" in history else None
        if close is None or close.empty:
            return None
        raw_rate = float(close.iloc[-1])
        factor = _fx_factor(source, target, raw_rate)
        if factor is None:
            return None
        result = {
            "rate": factor,
            "rawRate": raw_rate,
            "ticker": ticker,
            "date": pd.Timestamp(close.index[-1]).strftime("%Y-%m-%d"),
            "retrievedAt": int(time.time() * 1000),
        }
        cache_set(key, result, ttl=6 * 3600)
        return result
    except Exception:
        return None


def normalize_info(symbol: str, info: dict, fx: dict | None = None) -> tuple[dict, dict]:
    """Devuelve una copia de ``info`` lista para cálculos en moneda de mercado.

    Si no existe una conversión verificable, activa ``_currencyMismatch`` para
    que valoración, ratios y señales omitan resultados incompatibles.
    """
    out = copy.deepcopy(info or {})
    target = market_currency(symbol, out)
    source = str(out.get("financialCurrency") or target).upper()
    out["currency"] = target
    out["reportedFinancialCurrency"] = source

    if source == target:
        meta = {"status": "native", "source": source, "target": target, "rate": 1.0}
        out["_currencyMismatch"] = False
        out["_currencyConversion"] = meta
        return out, meta

    fx = fx if fx is not None else current_fx_rate(source, target)
    factor = fx.get("rate") if isinstance(fx, dict) else None
    if not _number(factor) or factor <= 0:
        meta = {"status": "unavailable", "source": source, "target": target, "rate": None}
        out["_currencyMismatch"] = True
        out["_currencyConversion"] = meta
        return out, meta

    for key in INFO_FINANCIAL_AMOUNTS:
        if _number(out.get(key)):
            out[key] *= factor

    # EPS y valor libro de Yahoo pueden venir en la moneda de los estados. Los
    # reconstruimos desde múltiplos adimensionales y el precio de mercado, que
    # es más seguro que adivinar la unidad del campo por acción.
    price = out.get("currentPrice") or out.get("regularMarketPrice")
    pe = out.get("trailingPE")
    fpe = out.get("forwardPE")
    pb = out.get("priceToBook")
    if _number(price) and price > 0:
        if _number(pe) and pe > 0:
            out["trailingEps"] = price / pe
        elif _number(out.get("trailingEps")):
            out["trailingEps"] *= factor
        if _number(fpe) and fpe > 0:
            out["forwardEps"] = price / fpe
        elif _number(out.get("forwardEps")):
            out["forwardEps"] *= factor
        if _number(pb) and pb > 0:
            out["bookValue"] = price / pb
        elif _number(out.get("bookValue")):
            out["bookValue"] *= factor

    meta = {
        "status": "converted",
        "source": source,
        "target": target,
        "rate": factor,
        "rawRate": fx.get("rawRate"),
        "ticker": fx.get("ticker"),
        "date": fx.get("date"),
        "retrievedAt": fx.get("retrievedAt"),
    }
    out["financialCurrency"] = target
    out["_currencyMismatch"] = False
    out["_currencyConversion"] = meta
    return out, meta


def convert_annuals(annuals: list[dict], conversion: dict) -> list[dict]:
    """Convierte filas anuales con la tasa actual usada por la valoración."""
    rows = copy.deepcopy(annuals or [])
    if conversion.get("status") != "converted":
        return rows
    factor = conversion["rate"]
    for row in rows:
        for key in ANNUAL_FINANCIAL_AMOUNTS:
            if _number(row.get(key)):
                row[key] *= factor
        for key in ("eps", "bvps"):
            if _number(row.get(key)):
                row[key] *= factor
        row["currency"] = conversion["target"]
        row["reportedCurrency"] = conversion["source"]
        row["fxRate"] = factor
    return rows


def convert_series(series: pd.Series | None, conversion: dict) -> pd.Series | None:
    if series is None or conversion.get("status") != "converted":
        return series
    return series.astype(float) * conversion["rate"]


def convert_fmp_rows(rows: list[dict] | None, conversion: dict) -> list[dict] | None:
    if not rows or conversion.get("status") != "converted":
        return rows
    out = copy.deepcopy(rows)
    factor = conversion["rate"]
    for row in out:
        for key in FMP_FINANCIAL_AMOUNTS:
            if _number(row.get(key)):
                row[key] *= factor
    return out


def convert_raw_estimates(raw, conversion: dict) -> None:
    """Convierte en una copia las tablas forward de Yahoo usadas por la grilla."""
    if conversion.get("status") != "converted":
        return
    factor = conversion["rate"]
    fields = {
        "earnings_estimate": {"avg", "low", "high", "yearAgoEps"},
        "revenue_estimate": {"avg", "low", "high", "yearAgoRevenue"},
    }
    for attr, columns in fields.items():
        frame = getattr(raw, attr, None)
        if frame is None or getattr(frame, "empty", True):
            continue
        converted = frame.copy(deep=True)
        for column in columns.intersection(set(converted.columns)):
            converted[column] = pd.to_numeric(converted[column], errors="coerce") * factor
        setattr(raw, attr, converted)
