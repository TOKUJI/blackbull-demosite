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

# Kill the running BlackBull process from a detached background job.
# Direct pkill would cause Alwaysdata to terminate this SSH session too.
# nohup + sleep ensures this script exits cleanly before the signal is delivered.
nohup sh -c 'sleep 1; pkill -f "blackbull blackbull_demo.app:app"' >/dev/null 2>&1 &
echo "Sent deferred termination signal — Alwaysdata will restart the process."

# Exit immediately — do not wait for restart verification (the SSH session
# would be terminated when Alwaysdata kills the User Program process).
exit 0
