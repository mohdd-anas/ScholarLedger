"""Application configuration via environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    DATABASE_URL: str = "postgresql://pb1:pb1secret@localhost:5432/pb1"

    # Security
    SECRET_KEY: str = "change-me-in-production-use-a-real-secret"
    SESSION_MAX_AGE: int = 3600 * 8  # 8 hours

    # External APIs (optional keys/tokens via environment variables)
    ORCID_API_BASE: str = "https://pub.orcid.org/v3.0"
    ORCID_ACCESS_TOKEN: str = ""
    OPENALEX_API_BASE: str = "https://api.openalex.org"
    OPENALEX_EMAIL: str = ""  # polite pool
    OPENALEX_API_KEY: str = ""
    CROSSREF_API_BASE: str = "https://api.crossref.org"
    CROSSREF_PLUS_API_TOKEN: str = ""

    # Matching thresholds
    MATCH_TITLE_THRESHOLD: float = 85.0
    MATCH_NAME_THRESHOLD: float = 80.0

    # App
    APP_NAME: str = "ScholarLedger"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()

