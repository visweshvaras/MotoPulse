#!/usr/bin/env bash
# ==============================================================================
# MotoPulse™ Cockpit - Launch Script
# ==============================================================================
# Launches the Python HTTP & WebSocket Telemetry Server and opens the browser.
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

echo "======================================================================"
echo "  🏎️  MOTOPULSE™ AI VEHICLE ACOUSTIC & VIBRATION TELEMETRY COCKPIT"
echo "  Target: http://localhost:8080"
echo "======================================================================"

# Fix serial permissions if /dev/ttyACM0 is present and not writable
if [ -e "/dev/ttyACM0" ]; then
    if [ ! -w "/dev/ttyACM0" ]; then
        sudo -n chmod 666 /dev/ttyACM0 2>/dev/null || true
    fi
    echo "✔ Checked /dev/ttyACM0 permissions"
fi

# Clean up any lingering server instances on ports 8080 or 8765
OLD_PID_8080=$(lsof -ti :8080 2>/dev/null || true)
if [ -n "${OLD_PID_8080}" ]; then
    echo "⚠️  Killing existing process on port 8080 (PID: ${OLD_PID_8080})..."
    kill -9 ${OLD_PID_8080} 2>/dev/null || true
fi

OLD_PID_8765=$(lsof -ti :8765 2>/dev/null || true)
if [ -n "${OLD_PID_8765}" ]; then
    echo "⚠️  Killing existing process on port 8765 (PID: ${OLD_PID_8765})..."
    kill -9 ${OLD_PID_8765} 2>/dev/null || true
fi

echo "🚀 Starting MotoPulse server (HTTP: 8080, WebSocket: 8765)..."
python3 dashboard/server.py &
SERVER_PID=$!

# Trap Ctrl+C or kill to shut down server cleanly
trap "echo -e '\n[SHUTDOWN] Stopping MotoPulse Server (PID: ${SERVER_PID})...'; kill ${SERVER_PID} 2>/dev/null || true; exit 0" INT TERM

# Wait for server to become responsive
echo -n "⏳ Waiting for HTTP server on http://localhost:8080..."
MAX_ATTEMPTS=30
ATTEMPT=0
while ! curl -s --head http://localhost:8080 >/dev/null 2>&1; do
    sleep 0.2
    ATTEMPT=$((ATTEMPT + 1))
    if [ ${ATTEMPT} -ge ${MAX_ATTEMPTS} ]; then
        echo -e "\n❌ Timeout waiting for server to start!"
        kill ${SERVER_PID} 2>/dev/null || true
        exit 1
    fi
    echo -n "."
done
echo " READY!"

echo "🌐 Opening MotoPulse Cockpit in your default web browser..."
if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "http://localhost:8080" >/dev/null 2>&1 &
elif command -v google-chrome >/dev/null 2>&1; then
    google-chrome "http://localhost:8080" >/dev/null 2>&1 &
elif command -v firefox >/dev/null 2>&1; then
    firefox "http://localhost:8080" >/dev/null 2>&1 &
fi

echo "======================================================================"
echo "  ✔ MotoPulse Cockpit is LIVE at http://localhost:8080"
echo "  ✔ WebSocket Telemetry streaming on ws://localhost:8765"
echo "  Press Ctrl+C at any time to stop the server."
echo "======================================================================"

# Wait on background server process
wait ${SERVER_PID}
