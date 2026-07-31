"""Extracción de transacciones de insiders y principales holders institucionales."""

from . import metrics as M


def _safe_int(v):
    """Convierte a int tolerando NaN/None/cadenas."""
    try:
        f = M._f(v)
        return int(f) if f is not None else None
    except (TypeError, ValueError):
        return None


def build_insiders_holders_payload(raw, info):
    """Extrae transacciones de insiders y principales fondos institucionales."""
    insiders = []
    try:
        if hasattr(raw, "insider_transactions") and raw.insider_transactions is not None and not raw.insider_transactions.empty:
            df = raw.insider_transactions.head(10)
            for _, row in df.iterrows():
                d_str = ""
                if "Start Date" in row and row["Start Date"] is not None:
                    d_str = str(row["Start Date"])[:10]
                insiders.append({
                    "insider": str(row.get("Insider", "—")),
                    "position": str(row.get("Position", "—")),
                    "transaction": str(row.get("Transaction", row.get("Text", "—"))),
                    "shares": M._f(row.get("Shares")),
                    "value": M._f(row.get("Value")),
                    "date": d_str,
                })
    except Exception:
        pass

    holders = []
    try:
        if hasattr(raw, "institutional_holders") and raw.institutional_holders is not None and not raw.institutional_holders.empty:
            df = raw.institutional_holders.head(10)
            for _, row in df.iterrows():
                d_str = ""
                if "Date Reported" in row and row["Date Reported"] is not None:
                    d_str = str(row["Date Reported"])[:10]
                holders.append({
                    "holder": str(row.get("Holder", "—")),
                    "shares": M._f(row.get("Shares")),
                    "value": M._f(row.get("Value")),
                    "pctChange": M._f(row.get("pctChange")),
                    "date": d_str,
                })
    except Exception:
        pass

    return {
        "insiders": insiders,
        "holders": holders,
        "insiderPercent": M._f(info.get("heldPercentInsiders")) * 100 if info.get("heldPercentInsiders") is not None else None,
        "institutionPercent": M._f(info.get("heldPercentInstitutions")) * 100 if info.get("heldPercentInstitutions") is not None else None,
    }