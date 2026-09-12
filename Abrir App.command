#!/bin/bash
set -e

APP_ROOT="$(cd "$(dirname "$0")" && pwd)"
APP_URL="http://127.0.0.1:8756/#/inicio"
LOG_FILE="$APP_ROOT/data/server.log"
EXPECTED_BUILD="2026.09.11.3"

if curl -fsS "http://127.0.0.1:8756/server-ready.js" 2>/dev/null | grep -q "$EXPECTED_BUILD"; then
  open "$APP_URL"
  exit 0
fi

# Si quedó una versión anterior de esta misma app, reemplazarla. No se toca
# ningún proceso que no sea uvicorn sirviendo backend.main en este puerto.
STALE_PID="$(lsof -tiTCP:8756 -sTCP:LISTEN 2>/dev/null || true)"
if [ -n "$STALE_PID" ]; then
  STALE_COMMAND="$(ps -p "$STALE_PID" -o command= 2>/dev/null || true)"
  if [[ "$STALE_COMMAND" == *"uvicorn backend.main:app"* ]]; then
    kill "$STALE_PID"
    for _ in $(seq 1 20); do
      lsof -tiTCP:8756 -sTCP:LISTEN >/dev/null 2>&1 || break
      sleep 0.1
    done
  else
    echo "El puerto 8756 está ocupado por otro programa: $STALE_COMMAND"
    read -r -p "Presiona Enter para cerrar…"
    exit 1
  fi
fi

PYTHON_BIN="$APP_ROOT/.venv/bin/python"
if [ ! -x "$PYTHON_BIN" ] && [ -x "$APP_ROOT/../../../.venv/bin/python" ]; then
  PYTHON_BIN="$APP_ROOT/../../../.venv/bin/python"
fi
if [ ! -x "$PYTHON_BIN" ]; then
  echo "No encontré .venv. Revisa las instrucciones de instalación en README.md."
  read -r -p "Presiona Enter para cerrar…"
  exit 1
fi

mkdir -p "$APP_ROOT/data"
nohup "$PYTHON_BIN" -m uvicorn backend.main:app --host 127.0.0.1 --port 8756 >"$LOG_FILE" 2>&1 &

for _ in $(seq 1 40); do
  if curl -fsS "http://127.0.0.1:8756/server-ready.js" 2>/dev/null | grep -q "$EXPECTED_BUILD"; then
    open "$APP_URL"
    exit 0
  fi
  sleep 0.25
done

echo "El servidor no pudo iniciar. Revisa: $LOG_FILE"
read -r -p "Presiona Enter para cerrar…"
exit 1
