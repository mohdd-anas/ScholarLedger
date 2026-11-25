"""Health, readiness, and Prometheus metrics endpoints."""

from fastapi import APIRouter, Depends
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Histogram,
    generate_latest,
)
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.responses import Response

from app.database import get_db

router = APIRouter(tags=["health"])

# Prometheus metrics
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
)


@router.get("/healthz")
def healthz():
    """Liveness probe — always returns 200 if the process is running."""
    return {"status": "healthy"}


@router.get("/readyz")
def readyz(db: Session = Depends(get_db)):
    """Readiness probe — returns 200 only if the database is reachable."""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ready", "database": "connected"}
    except Exception as e:
        return Response(
            content='{"status": "not ready", "database": "error: ' + str(e) + '"}',
            status_code=503,
            media_type="application/json",
        )


@router.get("/metrics")
def metrics():
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

