#!/bin/bash
# Lanza El Inversor Inteligente.
cd "$(dirname "$0")"
source .venv/bin/activate 2>/dev/null || true

HOST="127.0.0.1"

if [ "$1" = "--lan" ] || [ "$BIND_LAN" = "1" ]; then
  HOST="0.0.0.0"
  IP=$(ipconfig getifaddr en0 2>/dev/null || echo "localhost")
  echo "⚠️ ADVERTENCIA: Servidor expuesto en la red local (0.0.0.0)."
  echo "  En este equipo:  http://127.0.0.1:8756"
  echo "  Desde tu iPhone: http://$IP:8756  (misma red WiFi)"
else
  echo "◆ El Inversor Inteligente (modo local seguro)"
  echo "  Acceso local:    http://127.0.0.1:8756"
  echo "  (Para habilitar acceso en tu red local usa: ./run.sh --lan)"
fi

exec uvicorn backend.main:app --host "$HOST" --port 8756
