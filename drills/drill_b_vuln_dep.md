# Drill B: Vulnerable Dependency (pip-audit Gate)

## Objective
Verify that **Stage 3 (SCA — pip-audit)** blocks builds when a dependency has a known CVE with an available fix.

## Expected Behavior
- `pip-audit --strict` checks all installed Python packages against the PyPA Advisory Database.
- If any package has a known vulnerability with a fix available, `sca` exits with code 1 and blocks `build`.

## Scripted Drill
Run `./drills/run_drill_b.sh` to test `pip-audit` against a known vulnerable package version (e.g., `urllib3==1.26.4` or `requests==2.25.0`) in an isolated venv.

### Manual Steps
1. Create a test branch: `git checkout -b drill/b-vuln-dep`
2. Pin a known vulnerable dependency in `pyproject.toml` (e.g., `"requests==2.25.0"`).
3. Push to trigger CI (or run `pip-audit --strict` in an isolated venv).
4. **Observe:** Stage 3 (`📦 Dependency Audit (SCA)`) fails and blocks Stage 4 (`build`).
5. **Cleanup:** `git checkout main && git branch -D drill/b-vuln-dep`.
