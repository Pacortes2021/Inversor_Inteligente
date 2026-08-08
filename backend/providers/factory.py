"""Factoría de proveedores de datos con selección dinámica y fusión inteligente (Smart Merging)."""

import os
import logging
from typing import Dict, Any
from .fmp import FMPProvider
from .yfinance_provider import YFinanceProvider

logger = logging.getLogger(__name__)

def fetch_data_with_fallback(symbol: str) -> Dict[str, Any]:
    api_key = os.environ.get("FMP_API_KEY", "").strip()

    # 1. Si no hay API key de FMP, usar yfinance directo
    if not api_key:
        logger.info(f"Descargando {symbol} mediante yfinance (no hay FMP_API_KEY)...")
        yf_prov = YFinanceProvider()
        res = yf_prov.fetch_raw_data(symbol)
        res["provider"] = "yfinance"
        res["isFallback"] = True
        return res

    # 2. Intentar FMP primero
    logger.info(f"Intentando descargar {symbol} vía Financial Modeling Prep (FMP)...")
    fmp_data = {}
    try:
        fmp = FMPProvider(api_key=api_key)
        fmp_data = fmp.fetch_raw_data(symbol)
    except Exception as e:
        logger.error(f"Error descargando FMP para {symbol}: {e}")

    # Evaluar si FMP entregó datos fundamentales válidos (perfil/empresa + estados financieros)
    has_fmp_info = bool(fmp_data.get("info") and fmp_data["info"].get("shortName"))
    has_fmp_financials = bool(fmp_data.get("inc_a") is not None or fmp_data.get("inc_q") is not None)

    # 3. Si FMP falló por completo en la empresa o estados financieros, recurrir a yfinance
    if not (has_fmp_info and has_fmp_financials):
        logger.info(f"FMP sin cobertura completa para {symbol}. Usando yfinance...")
        yf_prov = YFinanceProvider()
        yf_data = yf_prov.fetch_raw_data(symbol)

        if not has_fmp_info:
            yf_data["provider"] = "yfinance (Fallback)"
            yf_data["isFallback"] = True
            return yf_data

        # Fusión parcial
        merged = yf_data.copy()
        for k, v in fmp_data.items():
            if v is not None:
                if hasattr(v, "empty") and v.empty:
                    continue
                if isinstance(v, dict) and not v:
                    continue
                merged[k] = v
        merged["provider"] = "FMP + yfinance Hybrid"
        merged["isFallback"] = True
        return merged

    # 4. FMP entregó exitosamente fundamentales auditados: fusionar precios y campos secundarios de yfinance
    logger.info(f"Datos fundamentales de {symbol} obtenidos con éxito desde FMP Premium.")
    yf_prov = YFinanceProvider()
    yf_data = yf_prov.fetch_raw_data(symbol)

    merged = fmp_data.copy()
    # FMI entrega fundamentales auditados. Si FMP no incluye precios EOD históricos, los toma de yfinance.
    for k in ["prices", "inc_a", "inc_q", "bs_a", "bs_q", "cf_a", "cf_q", "dividends", "insider_transactions", "institutional_holders", "shares", "recommendations", "news"]:
        val = merged.get(k)
        if val is None or (hasattr(val, "empty") and val.empty):
            if yf_data.get(k) is not None:
                merged[k] = yf_data[k]

    merged["provider"] = "Financial Modeling Prep (FMP)"
    merged["isFallback"] = False
    return merged

