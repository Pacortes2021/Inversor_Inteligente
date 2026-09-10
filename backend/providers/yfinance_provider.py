"""Proveedor de datos Yahoo Finance (yfinance) como fallback."""

import logging
import time
import pickle
from pathlib import Path
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any
from .base import BaseDataProvider
from ..yfinance_wrapper import (
    safe_calendar, safe_dividends, safe_earnings_dates, safe_earnings_estimate,
    safe_financials, safe_history, safe_info, safe_insider_transactions,
    safe_institutional_holders, safe_news, safe_recommendations,
    safe_revenue_estimate, safe_shares, safe_ticker,
)

logger = logging.getLogger(__name__)

YF_CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "cache" / "yf"
YF_CACHE_DIR.mkdir(parents=True, exist_ok=True)

class YFinanceProvider(BaseDataProvider):

    @staticmethod
    def _safe(fn):
        try:
            out = fn()
            if out is None:
                return None
            if hasattr(out, "empty") and out.empty:
                return None
            return out
        except Exception:
            return None

    def fetch_raw_data(self, symbol: str, refresh: bool = False) -> Dict[str, Any]:
        symbol = symbol.upper().strip()
        try:
            from ..config import CACHE_VERSION
        except Exception:
            CACHE_VERSION = "v0"
        safe_sym = symbol.replace('/', '_')
        cache_file = YF_CACHE_DIR / f"{safe_sym}_{CACHE_VERSION}.pkl"

        # 1. Leer de caché en disco (válido por 6 horas)
        if not refresh and cache_file.exists():
            try:
                if time.time() - cache_file.stat().st_mtime < 21600:
                    with open(cache_file, "rb") as f:
                        return pickle.load(f)
            except Exception as e:
                logger.warning(f"Error leyendo caché yf para {symbol}: {e}")

        start = (pd.Timestamp.now() - pd.DateOffset(years=10)).strftime("%Y-%m-%d")

        ticker = safe_ticker(symbol)
        info_data = self._safe(lambda: safe_info(ticker)) or {}

        tasks = {
            "prices": lambda: safe_history(ticker, period="max", interval="1d", auto_adjust=True),
            "inc_a": lambda: safe_financials(ticker, "income_stmt"),
            "inc_q": lambda: safe_financials(ticker, "quarterly_income_stmt"),
            "bs_a": lambda: safe_financials(ticker, "balance_sheet"),
            "bs_q": lambda: safe_financials(ticker, "quarterly_balance_sheet"),
            "cf_a": lambda: safe_financials(ticker, "cashflow"),
            "cf_q": lambda: safe_financials(ticker, "quarterly_cashflow"),
            "dividends": lambda: safe_dividends(ticker),
            "calendar": lambda: safe_calendar(ticker),
            "shares": lambda: safe_shares(ticker, start),
            "recommendations": lambda: safe_recommendations(ticker),
            "earnings_estimate": lambda: safe_earnings_estimate(ticker),
            "revenue_estimate": lambda: safe_revenue_estimate(ticker),
            "earnings_dates": lambda: safe_earnings_dates(ticker),
            "insider_transactions": lambda: safe_insider_transactions(ticker),
            "institutional_holders": lambda: safe_institutional_holders(ticker),
            "news": lambda: safe_news(ticker),
        }

        with ThreadPoolExecutor(max_workers=6) as ex:
            futures = {name: ex.submit(self._safe, fn) for name, fn in tasks.items()}
            results = {name: fut.result() for name, fut in futures.items()}

        prices = results["prices"]
        if prices is not None and not prices.empty:
            prices.index = prices.index.tz_localize(None)

        dividends = results["dividends"]
        if dividends is not None and not dividends.empty:
            dividends.index = dividends.index.tz_localize(None)

        shares = results["shares"]
        if shares is not None and not shares.empty:
            shares.index = shares.index.tz_localize(None)
            shares = shares[~shares.index.duplicated(keep="last")]

        res = {
            "provider": "yfinance",
            "info": info_data,
            "prices": prices,
            "inc_a": results["inc_a"],
            "inc_q": results["inc_q"],
            "bs_a": results["bs_a"],
            "bs_q": results["bs_q"],
            "cf_a": results["cf_a"],
            "cf_q": results["cf_q"],
            "dividends": dividends,
            "calendar": results["calendar"] or {},
            "shares": shares,
            "recommendations": results["recommendations"],
            "earnings_estimate": results["earnings_estimate"],
            "revenue_estimate": results["revenue_estimate"],
            "earnings_dates": results["earnings_dates"],
            "insider_transactions": results["insider_transactions"],
            "institutional_holders": results["institutional_holders"],
            "news": results["news"],
        }

        if info_data and len(info_data) > 5:
            try:
                with open(cache_file, "wb") as f:
                    pickle.dump(res, f)
            except Exception as e:
                logger.warning(f"Error escribiendo caché yf para {symbol}: {e}")

        return res
