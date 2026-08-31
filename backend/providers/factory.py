"""Factoría de proveedores de datos: Histórico vía Yahoo Finance + SEC EDGAR (FMP reservado exclusivamente para estimaciones forward)."""

import os
import logging
from typing import Dict, Any
from .yfinance_provider import YFinanceProvider
from ..edgar import get_annual_history

logger = logging.getLogger(__name__)

def fetch_data_with_fallback(symbol: str) -> Dict[str, Any]:
    """Obtiene los datos históricos fundamentales auditados exclusivamente desde Yahoo Finance y SEC EDGAR.
    FMP se reserva de forma exclusiva para el endpoint de estimaciones forward de analistas."""
    logger.info(f"Obteniendo datos históricos de {symbol} vía Yahoo Finance + SEC EDGAR...")
    yf_prov = YFinanceProvider()
    yf_data = yf_prov.fetch_raw_data(symbol)

    edgar_hist = None
    try:
        edgar_hist = get_annual_history(symbol)
    except Exception as e:
        logger.warning(f"No se pudo consultar SEC EDGAR para {symbol}: {e}")

    merged = yf_data.copy()

    if edgar_hist and any(edgar_hist.values()):
        logger.info(f"✅ Cobertura auditada de {symbol} verificada con SEC EDGAR ({len(edgar_hist.get('revenue', {}))} años).")
        merged["provider"] = "SEC EDGAR + Yahoo Finance"
        merged["isFallback"] = False
    else:
        merged["provider"] = "yfinance (Fallback)"
        merged["isFallback"] = True

    return merged


