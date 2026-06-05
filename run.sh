#!/usr/bin/env sh
set -eu

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8765}"

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$SCRIPT_DIR"

if [ -n "${PYTHON:-}" ]; then
  PYTHON_BIN="$PYTHON"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
elif [ -x "/c/Users/cwu/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe" ]; then
  PYTHON_BIN="/c/Users/cwu/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe"
else
  echo "Python was not found. Set PYTHON=/path/to/python and retry." >&2
  exit 1
fi

echo "Starting stock analysis app at http://${HOST}:${PORT}"
exec "$PYTHON_BIN" app.py --host "$HOST" --port "$PORT"
