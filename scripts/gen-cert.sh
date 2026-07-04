#!/bin/bash
# gen-cert.sh — Generate a self-signed TLS certificate for LOCAL DEVELOPMENT ONLY
#
# ⚠️  SELF-SIGNED — browsers will show a security warning.  NOT for production.
#     The production demo on Alwaysdata uses their edge TLS (Let's Encrypt).
#     Use this script ONLY to test BlackBull's HTTP/2 stack locally.
#
# Usage (local dev):
#   ./scripts/gen-cert.sh
#   blackbull blackbull_demo.app:app --bind :8443 \
#       --certfile certs/cert.pem --keyfile certs/key.pem
#
# Production (Alwaysdata):
#   TLS is terminated at Alwaysdata's edge — no cert needed in the app.
#   BlackBull receives plain HTTP/1.1 from the edge proxy.
#   See: blackbull-demo-site-requirements.md §2.3
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CERT_DIR="${SCRIPT_DIR}/../certs"
mkdir -p "${CERT_DIR}"

echo "Generating self-signed TLS certificate for localhost..."
openssl req -x509 -newkey rsa:2048 -nodes \
    -keyout "${CERT_DIR}/key.pem" \
    -out "${CERT_DIR}/cert.pem" \
    -days 365 \
    -subj "/C=JP/ST=Tokyo/L=Tokyo/O=BlackBull Demo/CN=localhost" \
    -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"

chmod 600 "${CERT_DIR}/key.pem"
echo "Done: certs/cert.pem, certs/key.pem"
echo ""
echo "Start with HTTP/2:"
echo "  blackbull blackbull_demo.app:app --bind :8443 --certfile certs/cert.pem --keyfile certs/key.pem"
