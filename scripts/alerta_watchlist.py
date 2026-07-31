#!/usr/bin/env python
"""Alerta diaria de watchlist: reevalúa el margen de seguridad de tus acciones
seguidas y manda una notificación de macOS si alguna entró en zona de compra.

Programada vía launchd (ver scripts/instalar_alerta.sh). Para desactivarla:
  launchctl unload ~/Library/LaunchAgents/com.inversorinteligente.watchlist.plist
"""

import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.watchlist import get_watchlist  # noqa: E402

LOG = ROOT / "data" / "alertas.log"

# Solo caracteres seguros para interpolación en AppleScript
_SAFE = re.compile(r"[^A-Za-z0-9\.\-\+% ]")


def _clean(s):
    return _SAFE.sub("", str(s or ""))


def notify(title: str, message: str):
    subprocess.run([
        "osascript", "-e",
        f'display notification "{_clean(message)}" with title "{_clean(title)}" sound name "Glass"',
    ], check=False, timeout=20)


def main():
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        items = get_watchlist()["items"]
    except Exception as e:
        with LOG.open("a") as f:
            f.write(f"{stamp} ERROR: {e}\n")
        return

    buy = [it for it in items if it.get("inBuyZone")]
    lines = [f"{it['symbol']} MoS {it.get('mos'):+.0f}% (objetivo {it.get('targetMos')}%)"
             for it in buy if it.get("mos") is not None]

    with LOG.open("a") as f:
        f.write(f"{stamp} evaluadas={len(items)} en_zona={len(buy)}"
                + (" | " + "; ".join(lines) if lines else "") + "\n")

    if buy:
        msg = ", ".join(f"{it['symbol']} ({it.get('mos'):+.0f}%)" for it in buy[:5])
        notify("◆ El Inversor Inteligente", f"En zona de compra: {msg}")


if __name__ == "__main__":
    main()
