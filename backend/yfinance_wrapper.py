"""Wrapper robusto para yfinance con retry/backoff y modo degradado (solo caché)."""

import os
import time
import random
import logging
from functools import wraps
from typing import Callable, Any

import yfinance as yf

from .config import (
    YF_MAX_RETRIES, YF_BASE_DELAY, YF_MAX_DELAY, YF_JITTER, YF_DEGRADED_MODE,
)

log = logging.getLogger(__name__)


def _should_retry(exc: Exception) -> bool:
    """Determina si una excepción es recuperable (rate limit, red, timeout)."""
    err_str = str(exc).lower()
    retryable = [
        "rate limit", "too many requests", "429", "503", "504",
        "timeout", "connection", "dns", "socket", "read timed out",
        "connect timed out", "temporary failure", "service unavailable",
    ]
    return any(r in err_str for r in retryable)


def _sleep_with_jitter(attempt: int) -> float:
    delay = min(YF_BASE_DELAY * (2 ** attempt), YF_MAX_DELAY)
    jitter_amt = delay * YF_JITTER * random.random()
    return delay + jitter_amt


def with_retry(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Decorador que reintenta llamadas a yfinance con backoff exponencial."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if YF_DEGRADED_MODE:
            raise RuntimeError("Modo degradado: yfinance deshabilitado")

        last_exc = None
        for attempt in range(YF_MAX_RETRIES + 1):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                last_exc = e
                if attempt < YF_MAX_RETRIES and _should_retry(e):
                    sleep_s = _sleep_with_jitter(attempt)
                    log.warning(
                        "yfinance %s falló (intento %d/%d): %s — reintentando en %.1fs",
                        fn.__name__, attempt + 1, YF_MAX_RETRIES + 1, e, sleep_s
                    )
                    time.sleep(sleep_s)
                    continue
                break
        raise last_exc
    return wrapper


# ─── Wrappers de alto nivel para operaciones comunes ───

@with_retry
def safe_ticker(symbol: str) -> yf.Ticker:
    """Crea un Ticker (sin I/O de red)."""
    return yf.Ticker(symbol)


@with_retry
def safe_info(ticker: yf.Ticker) -> dict:
    """Obtiene .info con reintentos."""
    return ticker.info or {}


@with_retry
def safe_history(ticker: yf.Ticker, **kwargs) -> Any:
    """Obtiene .history() con reintentos."""
    return ticker.history(**kwargs)


@with_retry
def safe_financials(ticker: yf.Ticker, attr: str) -> Any:
    """Obtiene un atributo financiero (income_stmt, balance_sheet, cashflow, etc.)."""
    return getattr(ticker, attr, None)


@with_retry
def safe_dividends(ticker: yf.Ticker) -> Any:
    return ticker.dividends


@with_retry
def safe_calendar(ticker: yf.Ticker) -> dict:
    return ticker.calendar or {}


@with_retry
def safe_shares(ticker: yf.Ticker, start: str) -> Any:
    return ticker.get_shares_full(start=start)


@with_retry
def safe_recommendations(ticker: yf.Ticker) -> Any:
    return ticker.recommendations


@with_retry
def safe_earnings_estimate(ticker: yf.Ticker) -> Any:
    return ticker.earnings_estimate


@with_retry
def safe_revenue_estimate(ticker: yf.Ticker) -> Any:
    return ticker.revenue_estimate


@with_retry
def safe_earnings_dates(ticker: yf.Ticker) -> Any:
    return ticker.earnings_dates


@with_retry
def safe_insider_transactions(ticker: yf.Ticker) -> Any:
    return ticker.insider_transactions


@with_retry
def safe_institutional_holders(ticker: yf.Ticker) -> Any:
    return ticker.institutional_holders


@with_retry
def safe_news(ticker: yf.Ticker) -> Any:
    return ticker.news


@with_retry
def safe_download(symbols, **kwargs) -> Any:
    """yf.download con reintentos."""
    return yf.download(symbols, **kwargs)


def enable_degraded_mode():
    """Activa modo degradado (solo sirve caché, no llama a Yahoo)."""
    global YF_DEGRADED_MODE
    YF_DEGRADED_MODE = True
    log.warning("yfinance: MODO DEGRADADO activado — solo caché")


def disable_degraded_mode():
    global YF_DEGRADED_MODE
    YF_DEGRADED_MODE = False
    log.info("yfinance: Modo normal restaurado")


def is_degraded() -> bool:
    return YF_DEGRADED_MODE