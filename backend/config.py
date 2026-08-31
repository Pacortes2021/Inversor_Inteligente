"""Configuración centralizada: claves, versiones de caché, feature flags."""

import os

# Carga .env del repo si existe (claves locales no versionadas)
_env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
if os.path.isfile(_env_path):
    with open(_env_path, encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())

# ─── Auth ───
API_KEY = os.getenv("INVERSOR_API_KEY", "dev-secret-change-me")

# ─── Financial Modeling Prep (estimaciones forward de analistas) ───
# Clave gratis: site.financialmodelingprep.com (250 req/día). Vacía = solo Yahoo.
FMP_API_KEY = os.getenv("FMP_API_KEY", "")
FMP_TIMEOUT = float(os.getenv("FMP_TIMEOUT", "8"))
FMP_TTL = float(os.getenv("FMP_TTL", "43200"))  # 12h

# ─── Cache versioning (bump al cambiar esquema de payload) ───
CACHE_VERSION = "v32"

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