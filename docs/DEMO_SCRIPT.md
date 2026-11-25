# ScholarLedger Demo Script — 6-Week Delivery Mapping

This script maps the 6-week project plan to the implemented repository artifacts and live walkthrough steps.

---

## Week 1 — Skeleton & Foundations
- **Built:**
  - `pyproject.toml`, `Dockerfile` (multi-stage, non-root `appuser`), `docker-compose.yml`
  - SQLAlchemy 2.0 models (`Faculty`, `Publication`, `MatchDecision`, `SyncRun`) and Alembic setup
  - `/healthz`, `/readyz`, `/metrics` endpoints (`app/routes/health.py`)
  - `tests/conftest.py` + unit tests (`tests/unit/test_models.py`, `test_health.py`)
- **Demo Command:**
  ```bash
  pytest tests/unit -v
  ```

## Week 2 — App Core & Initial CI
- **Built:**
  - Argon2id password hashing + signed cookie sessions + CSRF protection (`app/auth/`)
  - Server-side RBAC (`Faculty`, `Admin`, `Viewer`)
  - Publication CRUD + search/filter/pagination + Jinja2/HTMX UI (`app/routes/publications.py`)
  - Stage 1–2 CI (`secret-scan`, `lint-test` with Postgres 16 service container)
- **Demo Command:**
  ```bash
  ruff check . && pytest -v
  ```

## Week 3 — Ingestion, Matching & Security Gates
- **Built:**
  - Official API clients: ORCID (`orcid.py`), OpenAlex (`openalex.py`), Crossref (`crossref.py`)
  - Faculty Google Scholar BibTeX/CSV upload parser (`scholar_import.py`)
  - Matching engine (`matching.py`: DOI → rapidfuzz title → author name fallback) & deduplication (`dedup.py`)
  - Sync orchestrator (`sync_service.py` + `scripts/sync_publications.py`)
  - Admin review queue (`app/routes/review.py`) + IQAC department reports & CSV export (`app/routes/reports.py`)
  - Stage 3–6 CI: CodeQL SAST, `pip-audit` SCA, Trivy image scan, Syft SPDX SBOM + Cosign keyless signing
- **Demo Command:**
  ```bash
  python scripts/sync_publications.py --source all --dry-run
  ```

## Week 4 — Staging & DAST
- **Built:**
  - `docker-compose.staging.yml` for self-hosted runner deployment
  - `scripts/smoke_test.sh` post-deploy verification
  - OWASP ZAP baseline scan (`.zap/rules.tsv`) gating promotion in `.github/workflows/ci.yml`

## Week 5 — Production Promotion, Rollback & Observability
- **Built:**
  - GitHub `production` Environment gate (requires manual reviewer approval) + Cosign signature verification before deploy
  - Automatic Stage 9 rollback (`rollback` job on `if: failure()`) restoring previous image tag
  - Structured JSON logging (`structlog`) + Loki config (`monitoring/loki-config.yml`)
  - Prometheus scrape config (`monitoring/prometheus.yml`) + Grafana dashboard (`monitoring/grafana/dashboard.json`)

## Week 6 — Failure Drills & Final Demo
- **Built:**
  - In-repo reviewed allowlist (`security/allowlist.yml`, `security/.gitleaks.toml`)
  - Four scripted failure drills in `drills/`:
    - Drill A (`run_drill_a.sh`): Fake secret → Gitleaks blocks
    - Drill B (`run_drill_b.sh`): Vulnerable dep → `pip-audit` blocks
    - Drill C (`run_drill_c.sh`): Vulnerable base image → Trivy blocks
    - Drill D (`run_drill_d.sh`): Broken build → smoke test fails → auto-rollback restores previous tag
- **Live Demo Flow:**
  1. `docker compose up --build -d`
  2. `python scripts/seed_data.py`
  3. Log in as Faculty (`alice@university.edu` / `password123!`), add publication or upload BibTeX/CSV, submit for review.
  4. Log in as Admin (`admin@university.edu` / `admin123!`), verify publication in `/review`.
  5. Log in as IQAC Viewer (`iqac@university.edu` / `viewer123!`), inspect `/reports` and download CSV.
  6. Run `bash drills/run_drill_b.sh` and `bash drills/run_drill_d.sh` to demonstrate automated security & rollback gates.
