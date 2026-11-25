# ScholarLedger: University Research Publication Tracking System

> *"The secure pipeline is the product; the publication tracker is what it ships."*

A full-stack web application for tracking university faculty research publications, with automated ingestion from ORCID, OpenAlex, and Crossref — delivered through a secure, automated CI/CD pipeline.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Browser (HTMX)                       │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│              FastAPI (Uvicorn, Python 3.12)             │
│  ┌──────────┬──────────┬──────────┬──────────────────┐  │
│  │   Auth   │  CRUD    │ Ingest   │   Reports        │  │
│  │ (Argon2) │ (RBAC)   │ (APIs)   │   (CSV export)   │  │
│  └──────────┴──────────┴──────────┴──────────────────┘  │
│  SQLAlchemy 2.0 + Alembic                               │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│              PostgreSQL 16                              │
└─────────────────────────────────────────────────────────┘
                   ▲         ▲         ▲
         ORCID API    OpenAlex    Crossref
```

## Quick Start

```bash
# Clone and start
git clone <repo-url> && cd pb1-publication-tracker
cp .env.example .env
docker compose up --build

# Access
open http://localhost:8000       # App
open http://localhost:9090       # Prometheus
open http://localhost:3000       # Grafana (admin/admin)
```

## Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0 |
| Database | PostgreSQL 16 |
| Frontend | Jinja2 + HTMX (server-rendered) |
| Auth | Argon2id hashing, session cookies, RBAC |
| Ingestion | ORCID / OpenAlex / Crossref APIs, BibTeX import |
| Matching | rapidfuzz (DOI → title similarity → name fallback) |
| CI/CD | GitHub Actions (Gitleaks → Lint → SAST/SCA → Build → Scan → Sign → Stage → Promote) |
| Monitoring | Prometheus + Grafana + Loki |

## User Roles

| Role | Capabilities |
|------|-------------|
| **Faculty** | Register, link ORCID, upload Scholar exports, manage own publications, confirm/reject matches |
| **Admin** | Verify/reject any record, work the review queue |
| **Viewer** (IQAC) | Search, department reports, CSV export |

## Project Structure

```
├── app/                    # FastAPI application
│   ├── auth/              # Authentication & RBAC
│   ├── models/            # SQLAlchemy models
│   ├── routes/            # API & page routes
│   ├── schemas/           # Pydantic validation
│   ├── services/          # Business logic & ingestion
│   ├── templates/         # Jinja2 HTML templates
│   └── static/            # CSS & JS assets
├── alembic/               # Database migrations
├── tests/                 # pytest test suite
├── scripts/               # CLI utilities
├── monitoring/            # Prometheus, Grafana, Loki config
├── security/              # Gitleaks config & allowlist
├── drills/                # CI/CD failure drill documentation
├── docs/                  # Architecture decisions & demo script
└── .github/workflows/     # CI/CD pipeline
```

## Development

```bash
# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check .

# Run locally (without Docker)
uvicorn app.main:app --reload
```

## CI/CD Pipeline

See `.github/workflows/ci.yml` for the full pipeline:

1. **Secret Scan** (Gitleaks)
2. **Lint + Test** (ruff + pytest)
3. **SAST + SCA** (CodeQL + pip-audit)
4. **Build** (multi-stage Docker)
5. **Image Scan** (Trivy)
6. **Sign + SBOM** (Syft + cosign)
7. **Staging** (Docker Compose + ZAP scan)
8. **Promotion** (manual approval → production)
9. **Rollback** (automatic on health-check failure)

## Documentation

- [Design Decisions](docs/DECISIONS.md)
- [Demo Script](docs/DEMO_SCRIPT.md)
- [Failure Drills](drills/)

## License

MIT

