#!/usr/bin/env bash
# ScholarLedger Post-deploy smoke test
set -euo pipefail

BASE_URL="${1:-http://localhost:8000}"

echo "=== ScholarLedger Smoke Test ==="
echo "Target: $BASE_URL"

# 1. Health check
echo -n "Health check... "
STATUS=$(curl -sf "$BASE_URL/healthz" | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])")
[ "$STATUS" = "healthy" ] && echo "OK" || { echo "FAIL ($STATUS)"; exit 1; }

# 2. Readiness check
echo -n "Readiness check... "
STATUS=$(curl -sf "$BASE_URL/readyz" | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])")
[ "$STATUS" = "ready" ] && echo "OK" || { echo "FAIL ($STATUS)"; exit 1; }

# 3. Metrics endpoint
echo -n "Metrics endpoint... "
curl -sf "$BASE_URL/metrics" > /dev/null && echo "OK" || { echo "FAIL"; exit 1; }

# 4. Root page loads
echo -n "Root page... "
HTTP_CODE=$(curl -so /dev/null -w "%{http_code}" "$BASE_URL/")
[ "$HTTP_CODE" = "200" ] && echo "OK" || { echo "FAIL (HTTP $HTTP_CODE)"; exit 1; }

echo "=== All smoke tests passed ==="

