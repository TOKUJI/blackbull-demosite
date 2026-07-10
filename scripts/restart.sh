#!/bin/bash
# restart.sh — Restart the BlackBull demo Service on Alwaysdata
#
# The app runs as an Alwaysdata *Service* (not User Program).
# Restart is done via the Alwaysdata API.
#
# Prerequisites:
#   - ALWAYSDATA_API_KEY env var (get from https://admin.alwaysdata.com/profile/api/)
#   - ALWAYSDATA_ACCOUNT env var (your Alwaysdata account name)
#
# Usage:
#   ALWAYSDATA_API_KEY=xxx ALWAYSDATA_ACCOUNT=blackbull ./scripts/restart.sh
#
# Or restart manually: Advanced > Services > restart in admin panel.
#
set -euo pipefail

ALWAYSDATA_API_KEY="${ALWAYSDATA_API_KEY:-}"
ALWAYSDATA_ACCOUNT="${ALWAYSDATA_ACCOUNT:-}"
SERVICE_ID="${SERVICE_ID:-26686}"

echo "=== Restarting BlackBull demo (Service ${SERVICE_ID}) ==="

if [[ -z "$ALWAYSDATA_API_KEY" ]]; then
    echo "⚠️  ALWAYSDATA_API_KEY not set."
    echo "   Manual: Advanced > Services > restart in admin panel."
    echo "   Or: set ALWAYSDATA_API_KEY + ALWAYSDATA_ACCOUNT env vars."
    exit 1
fi

if [[ -z "$ALWAYSDATA_ACCOUNT" ]]; then
    echo "Error: ALWAYSDATA_ACCOUNT is not set."
    exit 1
fi

# Restart via Alwaysdata API
curl -sS -X POST \
    -H "Authorization: Bearer ${ALWAYSDATA_API_KEY}" \
    "https://api.alwaysdata.com/v1/service/${SERVICE_ID}/restart/"

echo ""
echo "Service restart requested."
echo "  → Health check: curl https://${ALWAYSDATA_ACCOUNT}.alwaysdata.net/health"
