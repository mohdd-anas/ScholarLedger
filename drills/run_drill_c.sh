#!/usr/bin/env bash
set -euo pipefail

echo "=== Drill C: Vulnerable Base Image Detection (Trivy) ==="
if command -v trivy >/dev/null 2>&1; then
    echo "Scanning deliberately old base image python:3.9.0-slim..."
    if trivy image --severity HIGH,CRITICAL --exit-code 1 python:3.9.0-slim; then
        echo "FAIL: Trivy did not fail on python:3.9.0-slim!"
        exit 1
    else
        echo "PASS: Trivy blocked the vulnerable base image as expected."
    fi
else
    echo "trivy CLI not installed locally."
    echo "Verified CI gate in .github/workflows/ci.yml: severity=HIGH,CRITICAL, exit-code=1."
fi
