"""Faculty model."""

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class FacultyRole(str, enum.Enum):
    """User roles for RBAC."""

    FACULTY = "faculty"
    ADMIN = "admin"
    VIEWER = "viewer"


class Faculty(Base):
    """A university faculty member."""

    __tablename__ = "faculty"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    department: Mapped[str] = mapped_column(String(255), nullable=False)
    university: Mapped[str | None] = mapped_column(String(255), nullable=True)
    orcid_id: Mapped[str | None] = mapped_column(String(19), unique=True, nullable=True)
    role: Mapped[FacultyRole] = mapped_column(
        Enum(FacultyRole, native_enum=False), default=FacultyRole.FACULTY
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    publications = relationship("Publication", back_populates="owner")
    coauthored_publications = relationship(
        "Publication",
        secondary="publication_coauthor",
        back_populates="coauthors",
    )

    def __repr__(self) -> str:
        return f"<Faculty {self.name} ({self.email})>"

