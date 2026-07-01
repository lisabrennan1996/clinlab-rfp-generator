#!/bin/bash
# Central Lab RFP Generator — one-time server launcher
# This starts a local HTTP server (required by Pyodide/WASM).
# Open the URL in your browser — no install needed, just use the tab.

PORT=${PORT:-8000}
DIR="$(cd "$(dirname "$0")" && pwd)"

echo ""
echo "  ╔═══════════════════════════════════════════════╗"
echo "  ║   Central Lab RFP Generator                   ║"
echo "  ║                                               ║"
echo "  ║   Step 1: Open http://localhost:$PORT         ║"
echo "  ║          in your browser.                      ║"
echo "  ║                                               ║"
echo "  ║   Step 2: Upload PDFs → they parse instantly   ║"
echo "  ║                                               ║"
echo "  ║   Step 3: Click \"Next\" → Generate RFP         ║"
echo "  ║                                               ║"
echo "  ║   Close this terminal when done.               ║"
echo "  ╚═══════════════════════════════════════════════╝"
echo ""

cd "$DIR"
echo "Serving files from: $DIR"

# Try python3 first, then python
PYTHON=""
command -v python3 >/dev/null && PYTHON=python3
command -v python >/dev/null && PYTHON=python
if [ -z "$PYTHON" ]; then
  echo "ERROR: Python not found. Please install Python 3."
  exit 1
fi

$PYTHON -m http.server "$PORT" &
PID=$!
sleep 1.5

# Open browser
case "$(uname -s)" in
  Darwin) open "http://localhost:$PORT" ;;
  Linux)  xdg-open "http://localhost:$PORT" 2>/dev/null || true ;;
  MINGW*|MSYS*) start "http://localhost:$PORT" ;;
  *)      echo "Open http://localhost:$PORT in your browser." ;;
esac

echo "Server running. Press Ctrl+C to stop."
trap "kill $PID 2>/dev/null; exit 0" INT TERM
wait "$PID"
