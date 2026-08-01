"""Configuración centralizada: claves, versiones de caché, feature flags."""

import os

# ─── Auth ───
API_KEY = os.getenv("INVERSOR_API_KEY", "dev-secret-change-me")

# ─── Cache versioning (bump al cambiar esquema de payload) ───
CACHE_VERSION = "v4"

# ─── yfinance wrapper ───
YF_MAX_RETRIES = int(os.getenv("YF_MAX_RETRIES", "3"))
YF_BASE_DELAY = float(os.getenv("YF_BASE_DELAY", "1.0"))
YF_MAX_DELAY = float(os.getenv("YF_MAX_DELAY", "10.0"))
YF_JITTER = float(os.getenv("YF_JITTER", "0.5"))
YF_DEGRADED_MODE = os.getenv("YF_DEGRADED_MODE", "false").lower() == "true"

# ─── EDGAR ───
EDGAR_USER_AGENT = os.getenv("EDGAR_USER_AGENT", "ElInversorInteligente/1.0 (pacortes2021@udec.cl)")
EDGAR_MIN_INTERVAL = float(os.getenv("EDGAR_MIN_INTERVAL", "0.11"))

# ─── Timeouts ───
YF_TIMEOUT = int(os.getenv("YF_TIMEOUT", "45"))
EDGAR_TIMEOUT = int(os.getenv("EDGAR_TIMEOUT", "60"))