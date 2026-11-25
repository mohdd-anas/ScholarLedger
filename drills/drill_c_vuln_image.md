# Drill C: Vulnerable Container Base Image (Trivy Gate)

## Objective
Verify that **Stage 5 (Image Scan — Trivy)** blocks any container image with `HIGH` or `CRITICAL` vulnerabilities from reaching Stage 6 (Sign + SBOM) and deployment.

## Expected Behavior
- `aquasecurity/trivy-action` scans the newly built image with `severity: "HIGH,CRITICAL"` and `exit-code: "1"`.
- Any `HIGH` or `CRITICAL` OS or library CVE fails the build and uploads SARIF results to GitHub Security.

## Scripted Drill
Run `./drills/run_drill_c.sh` to scan a deliberately outdated base image (e.g., `python:3.9.0-slim`) with Trivy if installed, or verify the Dockerfile gate configuration.

### Manual Steps
1. Create a test branch: `git checkout -b drill/c-vuln-image`
2. Temporarily change `FROM python:3.12-slim` in `Dockerfile` to `FROM python:3.9.0-slim`.
3. Push to trigger CI (or run `trivy image --severity HIGH,CRITICAL --exit-code 1 python:3.9.0-slim`).
4. **Observe:** Stage 5 (`🔍 Image Scan (Trivy)`) fails with exit code 1. Stage 6 (`sign-sbom`) never runs, so no unsigned/vulnerable image is signed or deployed.
5. **Cleanup:** `git checkout main && git branch -D drill/c-vuln-image`.
