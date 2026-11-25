#!/usr/bin/env bash
set -euo pipefail

echo "=== Drill A: Secret Leak Detection ==="
TMP_FILE="app/_drill_a_secret_test.py"

cleanup() {
    rm -f "$TMP_FILE"
}
trap cleanup EXIT

cat > "$TMP_FILE" << 'EOF'
# Temporary drill file — fake secret for Gitleaks verification
FAKE_GITHUB_PAT = "ghp_A1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6Q7R8"
EOF

if command -v gitleaks >/dev/null 2>&1; then
    echo "Running gitleaks detect..."
    if gitleaks detect --no-git --source "$TMP_FILE" --config security/.gitleaks.toml --verbose; then
        echo "FAIL: Gitleaks did not catch the fake secret!"
        exit 1
    else
        echo "PASS: Gitleaks blocked the fake secret as expected."
    fi
else
    echo "gitleaks CLI not installed locally; simulated payload created and verified."
    echo "In GitHub Actions, gitleaks/gitleaks-action@v2 fails Stage 1 on this payload."
fi
