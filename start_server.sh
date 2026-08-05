#!/usr/bin/env bash
# Arranque robusto del servidor: si uvicorn muere, se reinicia solo (2s).
# Uso: nohup ./start_server.sh > /dev/null 2>&1 &   (o: ./start_server.sh)
set -u
cd "$(dirname "$0")"
LOG="${OC_BACKEND_LOG:-/tmp/oc_backend.log}"
echo "── $(date '+%F %T') start_server.sh pid=$$" >> "$LOG"
while true; do
  .venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8756 >> "$LOG" 2>&1
  code=$?
  echo "── $(date '+%F %T') uvicorn salió (código $code) — reinicio en 2s" >> "$LOG"
  sleep 2
done
