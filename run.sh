#!/usr/bin/env sh
set -eu

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8765}"
ACTION="${1:-foreground}"

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$SCRIPT_DIR"

CACHE_DIR="$SCRIPT_DIR/.cache"
PID_FILE="$CACHE_DIR/server.pid"
LOG_FILE="$CACHE_DIR/server.log"

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

is_running() {
  [ -f "$PID_FILE" ] || return 1
  PID=$(cat "$PID_FILE")
  [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null
}

start_background() {
  mkdir -p "$CACHE_DIR"
  if is_running; then
    echo "Stock analysis app is already running (PID $PID)"
    echo "URL: http://${HOST}:${PORT}"
    return
  fi

  rm -f "$PID_FILE"
  nohup "$PYTHON_BIN" app.py --host "$HOST" --port "$PORT" >> "$LOG_FILE" 2>&1 &
  PID=$!
  echo "$PID" > "$PID_FILE"
  sleep 1

  if kill -0 "$PID" 2>/dev/null; then
    echo "Stock analysis app started in background (PID $PID)"
    echo "URL: http://${HOST}:${PORT}"
    echo "Log: $LOG_FILE"
  else
    rm -f "$PID_FILE"
    echo "Stock analysis app failed to start. Check $LOG_FILE" >&2
    exit 1
  fi
}

stop_background() {
  if ! is_running; then
    rm -f "$PID_FILE"
    echo "Stock analysis app is not running"
    return
  fi

  kill "$PID"
  rm -f "$PID_FILE"
  echo "Stock analysis app stopped (PID $PID)"
}

case "$ACTION" in
  foreground)
    echo "Starting stock analysis app at http://${HOST}:${PORT}"
    exec "$PYTHON_BIN" app.py --host "$HOST" --port "$PORT"
    ;;
  start)
    start_background
    ;;
  stop)
    stop_background
    ;;
  restart)
    stop_background
    start_background
    ;;
  status)
    if is_running; then
      echo "Stock analysis app is running (PID $PID)"
      echo "URL: http://${HOST}:${PORT}"
    else
      echo "Stock analysis app is not running"
      exit 1
    fi
    ;;
  *)
    echo "Usage: sh run.sh [start|stop|restart|status]" >&2
    exit 2
    ;;
esac
