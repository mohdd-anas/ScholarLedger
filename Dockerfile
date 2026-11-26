# ==============================
# Stage 1: Build
# ==============================
FROM python:3.12-slim AS builder

WORKDIR /build

RUN pip install --no-cache-dir --upgrade pip setuptools wheel

COPY pyproject.toml ./
RUN pip install --no-cache-dir ".[dev]" 2>/dev/null || pip install --no-cache-dir .
# Ensure the runtime site-packages do not retain the vulnerable setuptools
# version supplied by the base image or a package build dependency.
RUN pip install --no-cache-dir --upgrade "setuptools>=78.1.1"

COPY . .

# ==============================
# Stage 2: Runtime (non-root)
# ==============================
FROM python:3.12-slim AS runtime

# Apply current Debian security updates to the runtime OS packages.
RUN apt-get update \
    && apt-get upgrade -y \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Packaging tools are only needed in the builder. Remove setuptools from the
# runtime image so its vulnerable build-time copy cannot ship with the app.
RUN rm -rf /usr/local/lib/python3.12/site-packages/setuptools \
    /usr/local/lib/python3.12/site-packages/setuptools-*.dist-info

# Copy application code
COPY --chown=appuser:appuser app/ ./app/
COPY --chown=appuser:appuser alembic/ ./alembic/
COPY --chown=appuser:appuser alembic.ini ./
COPY --chown=appuser:appuser pyproject.toml ./
COPY --chown=appuser:appuser scripts/ ./scripts/

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import httpx; r = httpx.get('http://localhost:8000/healthz'); r.raise_for_status()"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]

