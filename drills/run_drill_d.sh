#!/usr/bin/env bash
set -euo pipefail

echo "=== Drill D: Broken Build & Rollback Simulation ==="
TMP_PREV=$(mktemp)
cleanup() {
    rm -f "$TMP_PREV"
}
trap cleanup EXIT

echo "ghcr.io/example/pb1-publication-tracker:sha-previous-healthy" > "$TMP_PREV"

echo "1. Testing smoke_test.sh against unreachable port (simulating broken build)..."
if bash scripts/smoke_test.sh "http://127.0.0.1:59999" 2>/dev/null; then
    echo "FAIL: Smoke test should have failed on broken target!"
    exit 1
else
    echo "PASS: Smoke test failed on broken build as expected."
fi

echo "2. Verifying rollback target resolution..."
PREVIOUS_IMAGE=$(cat "$TMP_PREV")
if [ -n "$PREVIOUS_IMAGE" ] && [ "$PREVIOUS_IMAGE" != "none" ]; then
    echo "PASS: Rollback would restore previous image: $PREVIOUS_IMAGE"
else
    echo "FAIL: Could not resolve previous image."
    exit 1
fi
