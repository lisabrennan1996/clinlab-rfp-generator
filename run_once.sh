#!/bin/bash
# Central Lab RFP Generator — one-time server launcher
# Run this once, install the PWA, then you can close this terminal.

PORT=${PORT:-8000}
DIR="$(cd "$(dirname "$0")" && pwd)"

echo ""
echo "  ╔═══════════════════════════════════════════════╗"
echo "  ║   Central Lab RFP Generator                   ║"
echo "  ║   Starting server on http://localhost:$PORT    ║"
echo "  ║                                               ║"
echo "  ║   Open the URL above in your browser.          ║"
echo "  ║   Click Install when prompted to go offline.   ║"
echo "  ║   Then close this terminal — it works offline. ║"
echo "  ╚═══════════════════════════════════════════════╝"
echo ""

cd "$DIR"
python3 -m http.server "$PORT" &
PID=$!
sleep 1.5

case "$(uname -s)" in
  Darwin) open "http://localhost:$PORT" ;;
  Linux)  xdg-open "http://localhost:$PORT" 2>/dev/null || true ;;
  *)      echo "Please open http://localhost:$PORT in your browser." ;;
esac

trap "kill $PID 2>/dev/null; exit 0" INT TERM
wait "$PID"
