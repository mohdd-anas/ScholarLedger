"""Sync run tracking model."""

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SyncStatus(str, enum.Enum):
    """Status of a sync run."""

    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


class SyncRun(Base):
    """Tracks each ingestion sync run."""

    __tablename__ = "sync_run"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[SyncStatus] = mapped_column(
        Enum(SyncStatus, native_enum=False), default=SyncStatus.RUNNING
    )
    records_fetched: Mapped[int] = mapped_column(Integer, default=0)
    records_merged: Mapped[int] = mapped_column(Integer, default=0)
    records_queued: Mapped[int] = mapped_column(Integer, default=0)

    def __repr__(self) -> str:
        return f"<SyncRun {self.source} {self.status} fetched={self.records_fetched}>"

