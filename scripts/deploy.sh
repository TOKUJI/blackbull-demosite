#!/bin/bash
# deploy.sh — Deploy blackbull-demo to Alwaysdata
#
# Usage:
#   ./scripts/deploy.sh
#
# Prerequisites:
#   - SSH key configured for Alwaysdata
#   - ALWAYSDATA_USER and ALWAYSDATA_HOST environment variables set
#     (or edit the values below)
#
set -euo pipefail

ALWAYSDATA_USER="${ALWAYSDATA_USER:-}"
ALWAYSDATA_HOST="${ALWAYSDATA_HOST:-ssh-${ALWAYSDATA_USER}.alwaysdata.net}"
REMOTE_PATH="${REMOTE_PATH:-/home/${ALWAYSDATA_USER}/blackbull-demo}"

if [[ -z "$ALWAYSDATA_USER" ]]; then
    echo "Error: ALWAYSDATA_USER environment variable is not set."
    echo "Usage: ALWAYSDATA_USER=youruser ./scripts/deploy.sh"
    exit 1
fi

echo "=== Deploying blackbull-demo to Alwaysdata ==="
echo "Target: ${ALWAYSDATA_USER}@${ALWAYSDATA_HOST}:${REMOTE_PATH}"

# 1. Sync main with remote and push
echo "[1/4] Syncing and pushing main branch..."
git fetch origin main
git checkout main
git pull --ff-only origin main
git checkout -
git push origin main

# 2. SSH: pull latest code on Alwaysdata
echo "[2/4] Pulling latest code on Alwaysdata..."
ssh "${ALWAYSDATA_USER}@${ALWAYSDATA_HOST}" \
    "cd ${REMOTE_PATH} && git pull origin main"

# 3. SSH: install/update dependencies
echo "[3/4] Updating dependencies..."
ssh "${ALWAYSDATA_USER}@${ALWAYSDATA_HOST}" \
    "cd ${REMOTE_PATH} && .venv/bin/pip install -e ."

# 4. Restart the service (kill process; supervisor auto-restarts)
echo "[4/4] Restarting service..."
ssh "${ALWAYSDATA_USER}@${ALWAYSDATA_HOST}" \
    "pkill -f '[b]lackbull blackbull_demo.app:app' || true"
echo "Signal sent — Alwaysdata Services supervisor will restart the process."

echo "=== Deploy complete ==="
echo "  → Health check: curl https://${ALWAYSDATA_USER}.alwaysdata.net/health"
