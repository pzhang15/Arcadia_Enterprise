#!/usr/bin/env bash
set -euo pipefail

PIDS="$(lsof -i :8080 -sTCP:LISTEN -t 2>/dev/null || true)"
if [ -z "$PIDS" ]; then
  echo "Nothing listening on port 8080."
  exit 0
fi

echo "Stopping process(es) on port 8080: $PIDS"
kill $PIDS 2>/dev/null || true
sleep 1
PIDS="$(lsof -i :8080 -sTCP:LISTEN -t 2>/dev/null || true)"
if [ -n "$PIDS" ]; then
  echo "Force stopping: $PIDS"
  kill -9 $PIDS 2>/dev/null || true
fi

if lsof -i :8080 -sTCP:LISTEN -t >/dev/null 2>&1; then
  echo "Port 8080 still in use."
  lsof -i :8080 -sTCP:LISTEN
  exit 1
fi

echo "Port 8080 is free."
