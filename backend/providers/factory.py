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
        return yf_prov.fetch_raw_data(symbol)

    # 2. Intentar FMP primero
    logger.info(f"Intentando descargar {symbol} vía Financial Modeling Prep (FMP)...")
    fmp_data = {}
    try:
        fmp = FMPProvider(api_key=api_key)
        fmp_data = fmp.fetch_raw_data(symbol)
    except Exception as e:
        logger.error(f"Error descargando FMP para {symbol}: {e}")

    # 3. Si FMP no entregó datos válidos de precios o perfil, usar yfinance completo
    fmp_prices = fmp_data.get("prices")
    if fmp_prices is None or fmp_prices.empty:
        logger.info(f"FMP no entregó precios para {symbol}. Fusionando datos con yfinance...")
        yf_prov = YFinanceProvider()
        yf_data = yf_prov.fetch_raw_data(symbol)
        
        if not fmp_data or not fmp_data.get("info"):
            return yf_data
        
        # Smart Merge: FMP (si entregó algo) + yfinance para completar campos faltantes
        merged = yf_data.copy()
        for k, v in fmp_data.items():
            if v is not None:
                if hasattr(v, "empty") and v.empty:
                    continue
                if isinstance(v, dict) and not v:
                    continue
                merged[k] = v
        merged["provider"] = "FMP + yfinance Hybrid"
        return merged

    # 4. Si FMP entregó precios y EEFF, complementar los campos secundarios (insiders, dividendos, etc.) desde yfinance
    logger.info(f"Datos principales de {symbol} obtenidos con éxito desde FMP.")
    yf_prov = YFinanceProvider()
    yf_data = yf_prov.fetch_raw_data(symbol)
    
    merged = fmp_data.copy()
    # Rellenar cualquier Dataframe o dict secundario faltante con yfinance
    for k in ["inc_a", "inc_q", "bs_a", "bs_q", "cf_a", "cf_q", "dividends", "insider_transactions", "institutional_holders", "shares", "recommendations"]:
        val = merged.get(k)
        if val is None or (hasattr(val, "empty") and val.empty):
            if yf_data.get(k) is not None:
                merged[k] = yf_data[k]
                
    merged["provider"] = "FMP (Premium Data)"
    return merged
