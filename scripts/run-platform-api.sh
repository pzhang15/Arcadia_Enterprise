#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

API_HEALTH="http://127.0.0.1:8080/api/health"

if lsof -i :8080 -sTCP:LISTEN -t >/dev/null 2>&1; then
  if curl -sf -m 2 "$API_HEALTH" >/dev/null 2>&1; then
    echo "Platform API already running on http://127.0.0.1:8080"
    echo "Stop it with: ./scripts/stop-platform-api.sh"
    exit 0
  fi
  echo "Port 8080 is in use but not healthy. Run: ./scripts/stop-platform-api.sh"
  lsof -i :8080 -sTCP:LISTEN
  exit 1
fi

uv sync --reinstall-package mirage-ai --reinstall-package arcadia-eval
exec env RELOAD=1 uv run python frontends/platform/server.py
