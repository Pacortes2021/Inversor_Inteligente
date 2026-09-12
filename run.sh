#!/bin/bash
# Lanza El Inversor Inteligente.
set -e
APP_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$APP_ROOT"

PYTHON_BIN="$APP_ROOT/.venv/bin/python"
if [ ! -x "$PYTHON_BIN" ] && [ -x "$APP_ROOT/../../../.venv/bin/python" ]; then
  # Compatibilidad con el worktree aislado usado por Codex.
  PYTHON_BIN="$APP_ROOT/../../../.venv/bin/python"
fi
if [ ! -x "$PYTHON_BIN" ]; then
  echo "No encontré el entorno Python. Ejecuta primero:"
  echo "  python3 -m venv .venv"
  echo "  .venv/bin/pip install -r requirements.txt"
  exit 1
fi

HOST="127.0.0.1"

if [ "$1" = "--lan" ] || [ "$BIND_LAN" = "1" ]; then
  HOST="0.0.0.0"
  IP=$(ipconfig getifaddr en0 2>/dev/null || echo "localhost")
  echo "⚠️ ADVERTENCIA: Servidor expuesto en la red local (0.0.0.0)."
  echo "  En este equipo:  http://127.0.0.1:8756"
  echo "  Desde tu iPhone: http://$IP:8756  (misma red WiFi)"
  if [ -z "$INVERSOR_API_KEY" ] && ! grep -Eq '^INVERSOR_API_KEY=.+$' .env 2>/dev/null; then
    echo "  Modo lectura: define INVERSOR_API_KEY para modificar portafolio, watchlist o notas."
  fi
else
  echo "◆ El Inversor Inteligente (modo local seguro)"
  echo "  Acceso local:    http://127.0.0.1:8756"
  echo "  (Para habilitar acceso en tu red local usa: ./run.sh --lan)"
fi

exec "$PYTHON_BIN" -m uvicorn backend.main:app --host "$HOST" --port 8756
