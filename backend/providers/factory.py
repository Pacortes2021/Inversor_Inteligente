"""Factoría de proveedores de datos con selección dinámica y fusión inteligente (Smart Merging)."""

import os
import logging
from typing import Dict, Any
from .fmp import FMPProvider
from .yfinance_provider import YFinanceProvider
from ..edgar import get_annual_history

logger = logging.getLogger(__name__)

def fetch_data_with_fallback(symbol: str) -> Dict[str, Any]:
    api_key = os.environ.get("FMP_API_KEY", "").strip()

    # 1. Intentar FMP primero si hay API key activa
    fmp_data = {}
    if api_key:
        try:
            fmp = FMPProvider(api_key=api_key)
            fmp_data = fmp.fetch_raw_data(symbol)
        except Exception as e:
            logger.error(f"Error descargando FMP para {symbol}: {e}")

    has_fmp_info = bool(fmp_data.get("info") and fmp_data["info"].get("shortName"))
    has_fmp_financials = bool(fmp_data.get("inc_a") is not None or fmp_data.get("inc_q") is not None)

    # 2. Si FMP entregó exitosamente datos fundamentales auditados
    if has_fmp_info and has_fmp_financials:
        logger.info(f"Datos fundamentales de {symbol} obtenidos con éxito desde FMP Premium.")
        yf_prov = YFinanceProvider()
        yf_data = yf_prov.fetch_raw_data(symbol)

        merged = fmp_data.copy()
        for k in ["prices", "inc_a", "inc_q", "bs_a", "bs_q", "cf_a", "cf_q", "dividends", "insider_transactions", "institutional_holders", "shares", "recommendations", "news"]:
            val = merged.get(k)
            if val is None or (hasattr(val, "empty") and val.empty):
                if yf_data.get(k) is not None:
                    merged[k] = yf_data[k]

        # Enriquecer info de FMP con campos exclusivos de yfinance
        yf_info = yf_data.get("info") or {}
        merged_info = merged.get("info") or {}
        YF_ONLY_FIELDS = [
            "forwardPE", "forwardEps", "trailingPE", "fullTimeEmployees",
            "longBusinessSummary", "trailingAnnualDividendYield", "dividendYield",
            "dividendRate", "payoutRatio", "trailingEps", "priceToBook",
            "priceToSalesTrailing12Months", "enterpriseToEbitda", "enterpriseToRevenue",
            "pegRatio", "trailingPegRatio", "beta", "shortRatio", "shortPercentOfFloat",
            "heldPercentInsiders", "returnOnEquity", "returnOnAssets",
            "grossMargins", "operatingMargins", "profitMargins",
            "earningsGrowth", "revenueGrowth", "currentRatio", "quickRatio",
            "debtToEquity", "targetMeanPrice", "recommendationKey",
            # Market data fields
            "sector", "industry", "marketCap", "sharesOutstanding",
            "fiftyTwoWeekHigh", "fiftyTwoWeekLow", "fiftyDayAverage", "twoHundredDayAverage",
            "volume", "averageVolume", "averageVolume10days",
            "previousClose", "open", "dayHigh", "dayLow",
            "postMarketPrice", "postMarketChangePercent",
            "freeCashflow", "totalCash", "totalDebt",
            "bookValue", "trailingAnnualDividendRate",
        ]
        for field in YF_ONLY_FIELDS:
            if not merged_info.get(field) and yf_info.get(field) is not None:
                merged_info[field] = yf_info[field]
        merged["info"] = merged_info

        merged["provider"] = "Financial Modeling Prep (FMP)"
        merged["isFallback"] = False
        return merged

    # 3. FMP no disponible o sin cuota: Usar SEC EDGAR (15-20 años auditados) + Yahoo Finance
    logger.info(f"Obteniendo datos de {symbol} vía SEC EDGAR + Yahoo Finance...")
    yf_prov = YFinanceProvider()
    yf_data = yf_prov.fetch_raw_data(symbol)

    edgar_hist = None
    try:
        edgar_hist = get_annual_history(symbol)
    except Exception as e:
        logger.warning(f"No se pudo consultar SEC EDGAR para {symbol}: {e}")

    merged = yf_data.copy()

    # Si FMP aportó datos parciales, mezclarlos
    if fmp_data:
        for k, v in fmp_data.items():
            if v is not None:
                if hasattr(v, "empty") and v.empty:
                    continue
                if isinstance(v, dict) and not v:
                    continue
                merged[k] = v

    # Recuperar campos críticos que solo yfinance provee, que pueden haberse
    # pisado si FMP aportó un dict 'info' parcial (sin forwardPE, employees, etc.)
    yf_info = yf_data.get("info") or {}
    merged_info = merged.get("info") or {}
    YF_ONLY_FIELDS = [
        "forwardPE", "forwardEps", "trailingPE", "fullTimeEmployees",
        "longBusinessSummary", "trailingAnnualDividendYield", "dividendYield",
        "dividendRate", "payoutRatio", "trailingEps", "priceToBook",
        "priceToSalesTrailing12Months", "enterpriseToEbitda", "enterpriseToRevenue",
        "pegRatio", "trailingPegRatio", "beta", "shortRatio", "shortPercentOfFloat",
        "heldPercentInsiders", "returnOnEquity", "returnOnAssets",
        "grossMargins", "operatingMargins", "profitMargins",
        "earningsGrowth", "revenueGrowth", "currentRatio", "quickRatio",
        "debtToEquity", "targetMeanPrice", "recommendationKey",
    ]
    for field in YF_ONLY_FIELDS:
        if not merged_info.get(field) and yf_info.get(field) is not None:
            merged_info[field] = yf_info[field]
    merged["info"] = merged_info

    if edgar_hist and any(edgar_hist.values()):
        logger.info(f"✅ Cobertura auditada de {symbol} verificada con SEC EDGAR ({len(edgar_hist.get('revenue', {}))} años).")
        merged["provider"] = "SEC EDGAR + Yahoo Finance"
        merged["isFallback"] = False
    else:
        merged["provider"] = "yfinance (Fallback)"
        merged["isFallback"] = True

    return merged


