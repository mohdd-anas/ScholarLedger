"""Match decision audit model."""

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MatchMethod(str, enum.Enum):
    """How the match was made."""

    DOI = "doi"
    TITLE = "title"
    NAME = "name"


class MatchVerdict(str, enum.Enum):
    """Human reviewer decision."""

    ACCEPTED = "accepted"
    REJECTED = "rejected"
    PENDING = "pending"


class MatchDecision(Base):
    """Audit trail for publication match decisions."""

    __tablename__ = "match_decision"

    id: Mapped[int] = mapped_column(primary_key=True)
    publication_id: Mapped[int] = mapped_column(ForeignKey("publication.id"), nullable=False)
    matched_by: Mapped[MatchMethod] = mapped_column(
        Enum(MatchMethod, native_enum=False), nullable=False
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)
    reviewer: Mapped[str | None] = mapped_column(String(255), nullable=True)
    decision: Mapped[MatchVerdict] = mapped_column(
        Enum(MatchVerdict, native_enum=False), default=MatchVerdict.PENDING
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    publication = relationship("Publication", back_populates="match_decisions")

    def __repr__(self) -> str:
        return f"<MatchDecision pub={self.publication_id} {self.matched_by}={self.score:.2f}>"

