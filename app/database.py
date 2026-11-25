"""Database engine, session factory, and declarative base."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all models."""


_engine = None
_SessionFactory = None


def get_engine():
    """Return (and cache) the SQLAlchemy engine."""
    global _engine  # noqa: PLW0603
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
    return _engine


def get_session_factory():
    """Return (and cache) the session factory."""
    global _SessionFactory  # noqa: PLW0603
    if _SessionFactory is None:
        _SessionFactory = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _SessionFactory


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session."""
    factory = get_session_factory()
    session = factory()
    try:
        yield session
    finally:
        session.close()


def reset_engine():
    """Reset cached engine and session factory (for testing)."""
    global _engine, _SessionFactory  # noqa: PLW0603
    _engine = None
    _SessionFactory = None

