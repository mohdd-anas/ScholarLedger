"""Shared test fixtures for ScholarLedger."""

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Use SQLite for local/unit tests — no Postgres dependency required. CI sets
# TEST_DATABASE_URL per step when it needs PostgreSQL integration coverage.
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "sqlite:///./test_pb1.db")

# Configure application settings before importing the app. Respect an explicit
# DATABASE_URL (used when integration tests select PostgreSQL).
os.environ.setdefault("DATABASE_URL", TEST_DATABASE_URL)
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production"

from app.database import Base, get_db  # noqa: E402
from app.main import create_app  # noqa: E402


@pytest.fixture(scope="session")
def engine():
    """Create a test database engine."""
    connect_args = {}
    if "sqlite" in TEST_DATABASE_URL:
        connect_args["check_same_thread"] = False
    eng = create_engine(TEST_DATABASE_URL, connect_args=connect_args)
    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)
    if os.path.exists("./test_pb1.db"):
        os.remove("./test_pb1.db")


@pytest.fixture
def db_session(engine):
    """Yield a database session that rolls back after each test."""
    connection = engine.connect()
    transaction = connection.begin()
    session_local = sessionmaker(bind=connection)
    session = session_local()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session):
    """Yield a FastAPI test client with the DB session overridden."""
    app = create_app()

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

