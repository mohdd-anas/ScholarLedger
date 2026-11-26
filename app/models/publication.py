"""Publication model."""

import enum
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

publication_coauthor = Table(
    "publication_coauthor",
    Base.metadata,
    Column("publication_id", ForeignKey("publication.id", ondelete="CASCADE"), primary_key=True),
    Column("faculty_id", ForeignKey("faculty.id", ondelete="CASCADE"), primary_key=True),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)


class PublicationStatus(str, enum.Enum):
    """Publication review status."""

    DRAFT = "draft"
    SUBMITTED = "submitted"
    VERIFIED = "verified"
    REJECTED = "rejected"


class PublicationSource(str, enum.Enum):
    """Where the publication record came from."""

    ORCID = "orcid"
    OPENALEX = "openalex"
    CROSSREF = "crossref"
    SCHOLAR_EXPORT = "scholar_export"
    MANUAL = "manual"


class PublicationType(str, enum.Enum):
    """Type of publication."""

    JOURNAL_ARTICLE = "journal-article"
    CONFERENCE_PAPER = "conference-paper"
    BOOK_CHAPTER = "book-chapter"
    BOOK = "book"
    THESIS = "thesis"
    PREPRINT = "preprint"
    OTHER = "other"


class Publication(Base):
    """A research publication record."""

    __tablename__ = "publication"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    authors: Mapped[str] = mapped_column(Text, nullable=False)
    venue: Mapped[str | None] = mapped_column(String(500), nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    doi: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    pub_type: Mapped[PublicationType] = mapped_column(
        Enum(PublicationType, native_enum=False), default=PublicationType.OTHER
    )
    department: Mapped[str | None] = mapped_column(String(255), nullable=True)
    university: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[PublicationStatus] = mapped_column(
        Enum(PublicationStatus, native_enum=False), default=PublicationStatus.DRAFT
    )
    source: Mapped[PublicationSource] = mapped_column(
        Enum(PublicationSource, native_enum=False), default=PublicationSource.MANUAL
    )
    owner_faculty_id: Mapped[int] = mapped_column(ForeignKey("faculty.id"), nullable=False)
    match_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    owner = relationship("Faculty", back_populates="publications")
    coauthors = relationship(
        "Faculty",
        secondary=publication_coauthor,
        back_populates="coauthored_publications",
        order_by="Faculty.name",
    )
    match_decisions = relationship("MatchDecision", back_populates="publication")

    @property
    def coauthor_ids(self) -> list[int]:
        """Return IDs of faculty members attributed as co-authors."""
        return [fac.id for fac in self.coauthors]

    def is_attributed_to(self, faculty_id: int) -> bool:
        """Return True if the faculty member owns or co-authors this publication."""
        return self.owner_faculty_id == faculty_id or any(
            fac.id == faculty_id for fac in self.coauthors
        )

    def __repr__(self) -> str:
        title_short = self.title[:50] if self.title else ""
        return f"<Publication '{title_short}...' ({self.year})>"

