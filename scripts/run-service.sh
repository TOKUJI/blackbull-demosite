#!/bin/bash
# run-service.sh — Alwaysdata Services entry point for BlackBull Demo
#
# Launched by Alwaysdata Services supervisor (Advanced > Services).
# The Apache reverse proxy (Web > Sites > Custom Apache) forwards
# edge-TLS-terminated traffic from blackbull.alwaysdata.net:443
# to this process on port 8300.
#
# Configuration in Alwaysdata admin panel:
#   Command:     /home/blackbull/blackbull-demo/scripts/run-service.sh
#   Work dir:    /home/blackbull/blackbull-demo
#   Monitoring:  pgrep -f "blackbull blackbull_demo.app:app"
#
set -euo pipefail
exec ~/blackbull-demo/.venv/bin/blackbull blackbull_demo.app:app --bind '[::]:8300'
