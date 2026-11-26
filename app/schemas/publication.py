"""Publication Pydantic schemas."""

from pydantic import BaseModel, Field


class PublicationCreate(BaseModel):
    """Schema for creating a publication."""

    title: str = Field(..., min_length=1)
    authors: str = Field(..., min_length=1)
    venue: str | None = None
    year: int | None = Field(None, ge=1900, le=2100)
    doi: str | None = None
    pub_type: str = "other"
    department: str | None = None
    university: str | None = None


class PublicationUpdate(BaseModel):
    """Schema for updating a publication."""

    title: str | None = None
    authors: str | None = None
    venue: str | None = None
    year: int | None = None
    doi: str | None = None
    pub_type: str | None = None
    department: str | None = None
    university: str | None = None
    status: str | None = None


class PublicationRead(BaseModel):
    """Schema for publication responses."""

    id: int
    title: str
    authors: str
    venue: str | None
    year: int | None
    doi: str | None
    pub_type: str
    department: str | None
    university: str | None = None
    status: str
    source: str
    owner_faculty_id: int
    coauthor_ids: list[int] = Field(default_factory=list)
    match_confidence: float | None

    model_config = {"from_attributes": True}

