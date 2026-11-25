# Drill D: Broken Build & Automatic Rollback

## Objective
Verify that **Stage 8/9 (Post-Deploy Health Check + Automatic Rollback)** detects a broken deployment and automatically restores the previous healthy container image tag.

## Expected Behavior
1. Before deploying the new image, Stage 8 records the currently running container's image tag in `/tmp/previous-image.txt`.
2. After deploying the new image, Stage 8 runs `curl -sf http://localhost:8000/healthz` and `scripts/smoke_test.sh`.
3. If the health check or smoke test fails, Stage 8 exits non-zero.
4. Stage 9 (`⏪ Rollback`, `if: failure()`) automatically reads `/tmp/previous-image.txt`, redeploys the previous image, and verifies `/healthz` returns `200 OK`.

## Scripted Drill
Run `./drills/run_drill_d.sh` to simulate a failing smoke test against a broken endpoint and verify the rollback script logic.

### Manual Steps
1. Deploy a healthy release `v1` on the runner.
2. Introduce a breaking change on a test branch (e.g., `/healthz` returns HTTP 500).
3. Merge/push to `main` and approve the `production` environment gate.
4. **Observe:** Stage 8 fails the post-deploy health check; Stage 9 (`rollback`) triggers automatically and restores `v1`.
