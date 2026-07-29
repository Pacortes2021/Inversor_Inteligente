#!/bin/bash
# Lanza El Inversor Inteligente.
# --host 0.0.0.0 permite abrirla desde el teléfono en tu red local.
cd "$(dirname "$0")"
source .venv/bin/activate
IP=$(ipconfig getifaddr en0 2>/dev/null || echo "localhost")
echo "◆ El Inversor Inteligente"
echo "  En este equipo:  http://127.0.0.1:8756"
echo "  Desde tu iPhone: http://$IP:8756  (misma red WiFi)"
exec uvicorn backend.main:app --host 0.0.0.0 --port 8756
