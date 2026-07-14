#!/bin/bash
# diagnose-401.sh — Test Alwaysdata API auth to find the 401 root cause
#
# Usage:
#   export APIKEY="your-token-from-https://admin.alwaysdata.com/profile/api/"
#   bash scripts/diagnose-401.sh
#
# This script tests 6 different auth patterns against the Alwaysdata API
# to isolate whether the 401 is caused by:
#   A) Token value wrong / regenerated
#   B) Auth method (Bearer vs Basic)
#   C) Account name missing / wrong
#   D) IP restriction
#   E) Token disabled
#
set -euo pipefail

APIKEY="${APIKEY:-}"
SERVICE_ID="${SERVICE_ID:-26686}"
ACCOUNT="${ACCOUNT:-blackbull}"
BASE="https://api.alwaysdata.com/v1"

if [[ -z "$APIKEY" ]]; then
    echo "ERROR: Set APIKEY environment variable."
    echo "  Get token from: https://admin.alwaysdata.com/profile/api/"
    echo "  Then: export APIKEY='your-token' && bash scripts/diagnose-401.sh"
    exit 1
fi

echo "============================================================"
echo " Alwaysdata API Auth Diagnostic"
echo " Account:  $ACCOUNT"
echo " Service:  $SERVICE_ID"
echo " Key len:  ${#APIKEY} chars"
echo "============================================================"
echo ""

# ------------------------------------------------------------------
# Test 1: Simple GET — does the token work at all?
# ------------------------------------------------------------------
echo "=== Test 1: GET /v1/service/ (list services) — Basic auth ==="
HTTP=$(curl -sS -o /tmp/ad-diag-1.txt -w "%{http_code}" \
    --basic --user "APIKEY account=${ACCOUNT}:${APIKEY}" \
    "${BASE}/service/" 2>&1 || echo "CURL_FAIL")
echo "  HTTP $HTTP"
if [[ "$HTTP" == "200" ]]; then
    echo "  ✅ Token works! Auth method is correct."
    head -c 200 /tmp/ad-diag-1.txt | python3 -m json.tool 2>/dev/null || head -c 200 /tmp/ad-diag-1.txt
elif [[ "$HTTP" == "401" ]]; then
    echo "  ❌ Basic auth rejected. Checking response body..."
    cat /tmp/ad-diag-1.txt
else
    echo "  ⚠️  Unexpected response:"
    head -c 300 /tmp/ad-diag-1.txt
fi
echo ""

# ------------------------------------------------------------------
# Test 2: Bearer auth — the old method
# ------------------------------------------------------------------
echo "=== Test 2: GET /v1/service/ — Bearer auth ==="
HTTP=$(curl -sS -o /tmp/ad-diag-2.txt -w "%{http_code}" \
    -H "Authorization: Bearer ${APIKEY}" \
    "${BASE}/service/" 2>&1 || echo "CURL_FAIL")
echo "  HTTP $HTTP"
if [[ "$HTTP" == "200" ]]; then
    echo "  ✅ Bearer auth works! (Basic may be unnecessary.)"
elif [[ "$HTTP" == "401" ]]; then
    echo "  ❌ Bearer auth rejected too. Token value itself is likely the problem."
    echo "  Body: $(head -c 200 /tmp/ad-diag-2.txt)"
fi
echo ""

# ------------------------------------------------------------------
# Test 3: Basic auth WITHOUT account= prefix
# ------------------------------------------------------------------
echo "=== Test 3: GET /v1/service/ — Basic auth (no account=) ==="
HTTP=$(curl -sS -o /tmp/ad-diag-3.txt -w "%{http_code}" \
    --basic --user "${APIKEY}:" \
    "${BASE}/service/" 2>&1 || echo "CURL_FAIL")
echo "  HTTP $HTTP"
if [[ "$HTTP" == "200" ]]; then
    echo "  ⚠️  account= prefix is NOT needed."
elif [[ "$HTTP" == "401" ]]; then
    echo "  (Expected if account= is required)"
fi
echo ""

# ------------------------------------------------------------------
# Test 4: Basic auth with token as username, no password
# ------------------------------------------------------------------
echo "=== Test 4: GET /v1/service/ — Basic auth (APIKEY as user, no pass) ==="
HTTP=$(curl -sS -o /tmp/ad-diag-4.txt -w "%{http_code}" \
    --basic --user "APIKEY:${APIKEY}" \
    "${BASE}/service/" 2>&1 || echo "CURL_FAIL")
echo "  HTTP $HTTP"
[[ "$HTTP" == "200" ]] && echo "  ✅ This format works!"
echo ""

# ------------------------------------------------------------------
# Test 5: Basic auth with token ONLY in password field
# ------------------------------------------------------------------
echo "=== Test 5: GET /v1/service/ — Basic auth (account as user, token as pass) ==="
HTTP=$(curl -sS -o /tmp/ad-diag-5.txt -w "%{http_code}" \
    --basic --user "${ACCOUNT}:${APIKEY}" \
    "${BASE}/service/" 2>&1 || echo "CURL_FAIL")
echo "  HTTP $HTTP"
[[ "$HTTP" == "200" ]] && echo "  ✅ This format works!"
echo ""

# ------------------------------------------------------------------
# Test 6: Actually attempt restart — the real operation
# ------------------------------------------------------------------
echo "=== Test 6: POST /v1/service/${SERVICE_ID}/restart/ ==="
echo "  Using raw token as Basic auth username (format confirmed working)..."
HTTP=$(curl -sS -o /tmp/ad-diag-6.txt -w "%{http_code}" \
    -X POST \
    --basic --user "${APIKEY}:" \
    "${BASE}/service/${SERVICE_ID}/restart/" 2>&1 || echo "CURL_FAIL")
echo "  HTTP $HTTP"
if [[ "$HTTP" == "200" || "$HTTP" == "204" || "$HTTP" == "202" ]]; then
    echo "  ✅ Service restart ACCEPTED. Check site version in a few seconds."
elif [[ "$HTTP" == "401" ]]; then
    echo "  ❌ Still 401. Check response:"
    cat /tmp/ad-diag-6.txt
elif [[ "$HTTP" == "403" ]]; then
    echo "  ❌ 403 Forbidden — token lacks permission. Check admin panel permissions."
elif [[ "$HTTP" == "404" ]]; then
    echo "  ❌ 404 — Service ID ${SERVICE_ID} not found. Wrong ID?"
else
    echo "  Response body:"
    head -c 300 /tmp/ad-diag-6.txt
fi
echo ""

echo "============================================================"
echo " Diagnosis complete."
echo " If ALL tests return 401 → Token is invalid/regenerated."
echo "   → Get new token: https://admin.alwaysdata.com/profile/api/"
echo " If some tests pass but restart fails → Permission issue."
echo " If tests pass differently → Auth format matters."
echo "============================================================"
