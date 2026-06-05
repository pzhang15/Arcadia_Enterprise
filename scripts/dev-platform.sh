#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

API_URL="${VITE_API_PROXY_TARGET:-http://127.0.0.1:8080}"
API_HEALTH="${API_URL%/}/api/health"

if lsof -i :8080 -sTCP:LISTEN -t >/dev/null 2>&1; then
  if ! curl -sf -m 2 "$API_HEALTH" >/dev/null 2>&1; then
    echo "Port 8080 is in use but not responding. Stop the stuck process:"
    lsof -i :8080 -sTCP:LISTEN
    exit 1
  fi
  echo "API already healthy at $API_URL"
  exec npm run dev --prefix frontends/platform
fi

uv sync

RELOAD=1 uv run python frontends/platform/server.py &
API_PID=$!
cleanup() {
  kill "$API_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "Waiting for API at $API_HEALTH ..."
for _ in $(seq 1 60); do
  if curl -sf -m 2 "$API_HEALTH" >/dev/null 2>&1; then
    echo "API ready."
    break
  fi
  if ! kill -0 "$API_PID" 2>/dev/null; then
    echo "API process exited before becoming healthy."
    exit 1
  fi
  sleep 0.5
done

if ! curl -sf -m 2 "$API_HEALTH" >/dev/null 2>&1; then
  echo "API did not become healthy in time."
  exit 1
fi

npm run dev --prefix frontends/platform
