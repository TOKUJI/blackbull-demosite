#!/bin/bash
# restart.sh — Restart the BlackBull demo daemon on Alwaysdata
#
# This script is intended to be run ON the Alwaysdata host.
# It kills any running BlackBull process; Alwaysdata's "User Program"
# supervisor auto-restarts the daemon on exit.
#
# Usage (on Alwaysdata host):
#   ./scripts/restart.sh
#
set -euo pipefail

echo "=== Restarting BlackBull demo ==="

# Kill the running BlackBull process.
# Alwaysdata "User Program" auto-restarts the daemon on exit.
if pkill -f "blackbull blackbull_demo.app:app"; then
    echo "Sent termination signal to BlackBull process."
else
    echo "No running BlackBull process found — Alwaysdata may start it fresh."
fi

# Brief pause to let the OS reap the old process
sleep 1

# Verify the new process comes up
for i in $(seq 1 10); do
    if pgrep -f "blackbull blackbull_demo.app:app" > /dev/null; then
        echo "✅ BlackBull restarted successfully (PID: $(pgrep -f 'blackbull blackbull_demo.app:app' | head -1))"
        exit 0
    fi
    echo "Waiting for restart (attempt ${i}/10)..."
    sleep 2
done

echo "⚠️  BlackBull did not restart within 20s."
echo "   Check Alwaysdata admin panel → Web → Sites → Save to restart manually."
exit 1
