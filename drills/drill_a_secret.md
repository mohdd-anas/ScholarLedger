# Drill A: Secret Leak Detection (Gitleaks Gate)

## Objective
Verify that **Stage 1 (Secret Scan — Gitleaks)** blocks any commit or PR containing hardcoded secrets, API keys, or tokens.

## Expected Behavior
- Gitleaks scans the full git history (`fetch-depth: 0`) using `security/.gitleaks.toml`.
- Any secret matching Gitleaks rules causes the `secret-scan` job to exit non-zero, blocking all downstream stages (`lint-test`, `codeql`, `sca`, `build`, `staging`, `production`).

## Scripted Drill
Run `./drills/run_drill_a.sh` (creates a temporary branch, commits a fake AWS/GitHub secret, runs `gitleaks` locally or pushes to trigger CI, then cleans up).

### Manual Steps
1. Create a test branch: `git checkout -b drill/a-fake-secret`
2. Add a fake secret to a tracked file (outside `security/.gitleaks.toml` allowlist):
   ```python
   # app/fake_leak.py
   AWS_SECRET_ACCESS_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
   GITHUB_TOKEN = "ghp_1234567890abcdef1234567890abcdef1234"
   ```
3. Commit and push (or run `gitleaks detect --config security/.gitleaks.toml --verbose`).
4. **Observe:** Stage 1 (`🔐 Secret Scan`) fails immediately with exit code 1. Downstream jobs never start.
5. **Cleanup:** `git checkout main && git branch -D drill/a-fake-secret`.
