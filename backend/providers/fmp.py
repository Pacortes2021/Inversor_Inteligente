"""Proveedor de datos Financial Modeling Prep (FMP) API (/stable/ & /v3/)."""

import os
import logging
import requests
import pandas as pd
from typing import Dict, Any, Optional
from .base import BaseDataProvider

logger = logging.getLogger(__name__)

FMP_STABLE_URL = "https://financialmodelingprep.com/stable"
FMP_V3_URL = "https://financialmodelingprep.com/api/v3"
FMP_V4_URL = "https://financialmodelingprep.com/api/v4"

class FMPProvider(BaseDataProvider):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("FMP_API_KEY", "").strip()

    def is_available(self) -> bool:
        return bool(self.api_key)

    def _get(self, endpoint: str, params: Optional[dict] = None, base_url: str = FMP_STABLE_URL) -> Optional[Any]:
        if not self.api_key:
            return None
        url = f"{base_url}/{endpoint}"
        p = {"apikey": self.api_key}
        if params:
            p.update(params)
        try:
            resp = requests.get(url, params=p, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, dict) and ("Error Message" in data or "error" in data):
                    logger.warning(f"FMP Error on {endpoint}: {data}")
                    return None
                return data
            else:
                logger.warning(f"FMP HTTP {resp.status_code} for {endpoint}")
                return None
        except Exception as e:
            logger.error(f"Error connecting to FMP {endpoint}: {e}")
            return None

    def fetch_raw_data(self, symbol: str) -> Dict[str, Any]:
        symbol = symbol.upper().strip()

        # Try /stable/ first, fall back to /v3/ if empty
        profiles = self._get("profile", params={"symbol": symbol}) or self._get(f"profile/{symbol}", base_url=FMP_V3_URL)
        profile = profiles[0] if profiles and isinstance(profiles, list) else {}

        quotes = self._get("quote", params={"symbol": symbol}) or self._get(f"quote/{symbol}", base_url=FMP_V3_URL)
        quote = quotes[0] if quotes and isinstance(quotes, list) else {}

        info = {
            "symbol": symbol,
            "shortName": profile.get("companyName") or quote.get("name"),
            "longName": profile.get("companyName") or quote.get("name"),
            "sector": profile.get("sector"),
            "industry": profile.get("industry"),
            "country": profile.get("country"),
            "exchange": profile.get("exchangeShortName") or profile.get("exchange"),
            "currency": profile.get("currency", "USD"),
            "marketCap": quote.get("marketCap") or profile.get("mktCap") or profile.get("marketCap"),
            "trailingPE": quote.get("pe") or profile.get("pe"),
            "forwardPE": quote.get("forwardPe"),
            "priceToBook": profile.get("pb"),
            "priceToSalesTrailing12Months": profile.get("priceToSales"),
            "dividendYield": (profile.get("lastDividend", 0) / quote.get("price", 1)) if quote.get("price") else None,
            "dividendRate": profile.get("lastDividend"),
            "beta": profile.get("beta"),
            "fiftyTwoWeekHigh": quote.get("yearHigh"),
            "fiftyTwoWeekLow": quote.get("yearLow"),
            "currentPrice": quote.get("price") or profile.get("price"),
            "previousClose": quote.get("previousClose"),
            "description": profile.get("description"),
            "website": profile.get("website"),
            "sharesOutstanding": quote.get("sharesOutstanding"),
        }

        # Historical Prices
        hist_raw = self._get(f"historical-price-full/{symbol}") or self._get(f"historical-price-full/{symbol}", base_url=FMP_V3_URL)
        prices_df = None
        if hist_raw and isinstance(hist_raw, dict) and "historical" in hist_raw:
            df = pd.DataFrame(hist_raw["historical"])
            if not df.empty and "date" in df.columns:
                df["Date"] = pd.to_datetime(df["date"])
                df.set_index("Date", inplace=True)
                df.sort_index(ascending=True, inplace=True)
                df.rename(columns={
                    "open": "Open", "high": "High", "low": "Low",
                    "close": "Close", "adjClose": "Adj Close", "volume": "Volume"
                }, inplace=True)
                prices_df = df[["Open", "High", "Low", "Close", "Volume"]]

        def stmt_to_df(stmt_list, fmp_to_yf_map):
            if not stmt_list or not isinstance(stmt_list, list):
                return None
            records = {}
            for item in stmt_list:
                dt_str = item.get("date")
                if not dt_str:
                    continue
                dt = pd.to_datetime(dt_str)
                col_dict = {}
                for fmp_key, yf_key in fmp_to_yf_map.items():
                    if fmp_key in item and item[fmp_key] is not None:
                        col_dict[yf_key] = item[fmp_key]
                records[dt] = col_dict
            if not records:
                return None
            return pd.DataFrame.from_dict(records, orient="columns")

        inc_map = {
            "revenue": "Total Revenue", "costOfRevenue": "Cost Of Revenue",
            "grossProfit": "Gross Profit", "operatingExpenses": "Operating Expenses",
            "operatingIncome": "Operating Income", "netIncome": "Net Income",
            "eps": "Basic EPS", "epsdiluted": "Diluted EPS", "ebitda": "EBITDA",
            "weightedAverageShsOut": "Basic Average Shares", "weightedAverageShsOutDil": "Diluted Average Shares",
        }
        inc_a_list = self._get("income-statement", params={"symbol": symbol, "limit": 15}) or self._get(f"income-statement/{symbol}", params={"limit": 15}, base_url=FMP_V3_URL)
        inc_q_list = self._get("income-statement", params={"symbol": symbol, "period": "quarter", "limit": 20}) or self._get(f"income-statement/{symbol}", params={"period": "quarter", "limit": 20}, base_url=FMP_V3_URL)
        inc_a = stmt_to_df(inc_a_list, inc_map)
        inc_q = stmt_to_df(inc_q_list, inc_map)

        bs_map = {
            "totalAssets": "Total Assets", "totalLiabilities": "Total Liabilities Net Minority Interest",
            "totalStockholdersEquity": "Stockholders Equity", "cashAndCashEquivalents": "Cash And Cash Equivalents",
            "totalDebt": "Total Debt", "netDebt": "Net Debt", "commonStock": "Common Stock", "retainedEarnings": "Retained Earnings",
        }
        bs_a_list = self._get("balance-sheet-statement", params={"symbol": symbol, "limit": 15}) or self._get(f"balance-sheet-statement/{symbol}", params={"limit": 15}, base_url=FMP_V3_URL)
        bs_q_list = self._get("balance-sheet-statement", params={"symbol": symbol, "period": "quarter", "limit": 20}) or self._get(f"balance-sheet-statement/{symbol}", params={"period": "quarter", "limit": 20}, base_url=FMP_V3_URL)
        bs_a = stmt_to_df(bs_a_list, bs_map)
        bs_q = stmt_to_df(bs_q_list, bs_map)

        cf_map = {
            "operatingCashFlow": "Operating Cash Flow", "capitalExpenditure": "Capital Expenditure",
            "freeCashFlow": "Free Cash Flow", "dividendsPaid": "Common Stock Dividend Paid", "netChangeInCash": "Changes In Cash",
        }
        cf_a_list = self._get("cash-flow-statement", params={"symbol": symbol, "limit": 15}) or self._get(f"cash-flow-statement/{symbol}", params={"limit": 15}, base_url=FMP_V3_URL)
        cf_q_list = self._get("cash-flow-statement", params={"symbol": symbol, "period": "quarter", "limit": 20}) or self._get(f"cash-flow-statement/{symbol}", params={"period": "quarter", "limit": 20}, base_url=FMP_V3_URL)
        cf_a = stmt_to_df(cf_a_list, cf_map)
        cf_q = stmt_to_df(cf_q_list, cf_map)

        # Ratios TTM
        ratios_ttm = self._get("ratios-ttm", params={"symbol": symbol}) or self._get(f"ratios-ttm/{symbol}", base_url=FMP_V3_URL)
        if ratios_ttm and isinstance(ratios_ttm, list) and ratios_ttm[0]:
            rt = ratios_ttm[0]
            if rt.get("peRatioTTM"): info["trailingPE"] = rt.get("peRatioTTM")
            if rt.get("priceToBookRatioTTM"): info["priceToBook"] = rt.get("priceToBookRatioTTM")
            if rt.get("priceToSalesRatioTTM"): info["priceToSalesTrailing12Months"] = rt.get("priceToSalesRatioTTM")

        # Analyst Consensus Recommendations
        recs = self._get("analyst-stock-recommendations", params={"symbol": symbol}) or self._get(f"analyst-stock-recommendations/{symbol}", base_url=FMP_V3_URL)
        recs_df = None
        if recs and isinstance(recs, list) and recs:
            recs_df = pd.DataFrame(recs)

        return {
            "provider": "FMP",
            "info": info,
            "prices": prices_df,
            "inc_a": inc_a,
            "inc_q": inc_q,
            "bs_a": bs_a,
            "bs_q": bs_q,
            "cf_a": cf_a,
            "cf_q": cf_q,
            "dividends": None,
            "calendar": {},
            "shares": None,
            "recommendations": recs_df,
            "earnings_estimate": None,
            "revenue_estimate": None,
            "earnings_dates": None,
            "insider_transactions": None,
            "institutional_holders": None,
            "news": None
        }
