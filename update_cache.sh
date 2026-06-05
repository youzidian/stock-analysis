#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$SCRIPT_DIR"

if [ -n "${PYTHON:-}" ]; then
  PYTHON_BIN="$PYTHON"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
else
  echo "Python was not found. Set PYTHON=/path/to/python and retry." >&2
  exit 1
fi

if [ -n "${SYMBOLS_FILE:-}" ]; then
  SYMBOLS_PATH="$SYMBOLS_FILE"
elif [ -f "symbols.xlsx" ]; then
  SYMBOLS_PATH="symbols.xlsx"
else
  SYMBOLS_PATH="symbols.txt"
fi
DELAY="${DELAY:-0.25}"
MARKETS="${MARKETS:-}"
TAGS="${TAGS:-}"

exec "$PYTHON_BIN" -m stock_analyzer.cache_builder \
  --symbols-file "$SYMBOLS_PATH" \
  --delay "$DELAY" \
  --markets "$MARKETS" \
  --tags "$TAGS"
