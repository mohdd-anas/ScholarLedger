# ScholarLedger Design Decisions Log

Every default chosen during implementation is recorded here.

| # | Decision | Choice | Rationale | Phase |
|---|----------|--------|-----------|-------|
| 1 | Password hashing | Argon2id (`argon2-cffi`) | OWASP recommendation for password storage | 1 |
| 2 | Session store | Signed cookies (`itsdangerous` via Starlette `SessionMiddleware`) | Simple, no Redis needed for a small app | 1 |
| 3 | Database driver | `psycopg2-binary` (sync) | Simpler than async for a template-rendered app; SQLAlchemy sync session | 1 |
| 4 | ORM style | SQLAlchemy 2.0 mapped columns | Type-safe, modern API | 1 |
| 5 | Enum storage | `native_enum=False` (VARCHAR) | Portable across PostgreSQL and SQLite (testing) | 1 |
| 6 | Test database | SQLite for unit tests, PostgreSQL service container for integration/CI | Fast local tests; realistic CI tests | 1 |
| 7 | Logging | `structlog` with JSON output | Structured, Loki-compatible, machine-parseable | 1 |
| 8 | Metrics | `prometheus-client` Python library | Direct /metrics endpoint, no sidecar needed | 1 |
| 9 | HTMX delivery | CDN (`unpkg.com`) in dev, vendored in production Docker image | Fast start; no build step | 1 |
| 10 | Fuzzy matching library | `rapidfuzz` (token_sort_ratio, threshold 85) | Fast C++ backend; configurable threshold | — |
| 11 | HTTP client | `httpx` | Native async support; respects rate limits | — |
| 12 | Container registry | GHCR (`ghcr.io`) | Free for public repos; integrated with GitHub Actions | — |
| 13 | Image signing | Cosign keyless (Fulcio + Rekor) | No key management; OIDC-based | — |
| 14 | SBOM format | SPDX JSON via Syft | Industry standard; machine-readable | — |
| 15 | Self-hosted runner label | `self-hosted` | Standard default | — |
| 16 | CSRF protection | Double-submit cookie pattern | Works with HTMX | 2 |

