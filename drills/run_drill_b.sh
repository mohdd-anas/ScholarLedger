#!/usr/bin/env bash
set -euo pipefail

echo "=== Drill B: Vulnerable Dependency Detection (pip-audit) ==="
TMP_REQ=$(mktemp)
cleanup() {
    rm -f "$TMP_REQ"
}
trap cleanup EXIT

# Known CVE in requests 2.25.0 (CVE-2023-32681)
echo "requests==2.25.0" > "$TMP_REQ"

if [ -x ".venv/bin/pip-audit" ]; then
    echo "Running pip-audit against vulnerable requirement..."
    if .venv/bin/pip-audit -r "$TMP_REQ" --strict; then
        echo "FAIL: pip-audit did not flag requests==2.25.0!"
        exit 1
    else
        echo "PASS: pip-audit blocked the vulnerable dependency as expected."
    fi
else
    echo "pip-audit not found in .venv; install dev deps first."
    exit 1
fi
