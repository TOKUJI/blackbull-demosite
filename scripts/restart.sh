#!/bin/bash
# restart.sh — Restart the BlackBull demo daemon on Alwaysdata
#
# This script is intended to be run ON the Alwaysdata host.
# It touches a watched file or signals the daemon to restart.
#
set -euo pipefail

APP_DIR="/home/${USER}/blackbull-demo"
PID_FILE="${APP_DIR}/.app.pid"

if [[ -f "${PID_FILE}" ]]; then
    OLD_PID=$(cat "${PID_FILE}")
    if kill -0 "${OLD_PID}" 2>/dev/null; then
        echo "Stopping old process (PID: ${OLD_PID})..."
        kill "${OLD_PID}"
        sleep 1
    fi
    rm -f "${PID_FILE}"
fi

echo "Starting BlackBull demo..."
cd "${APP_DIR}"
nohup .venv/bin/python -m blackbull_demo > /dev/null 2>&1 &
echo $! > "${PID_FILE}"
echo "Started with PID: $(cat ${PID_FILE})"
