"""Faculty Pydantic schemas."""

from pydantic import BaseModel, Field


class FacultyCreate(BaseModel):
    """Schema for faculty registration."""

    name: str = Field(..., min_length=1, max_length=255)
    email: str = Field(..., min_length=5, max_length=255)
    department: str = Field(..., min_length=1, max_length=255)
    university: str | None = Field(None, max_length=255)
    orcid_id: str | None = Field(None, pattern=r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$")
    password: str = Field(..., min_length=8, max_length=128)


class FacultyRead(BaseModel):
    """Schema for faculty responses."""

    id: int
    name: str
    email: str
    department: str
    university: str | None = None
    orcid_id: str | None
    role: str

    model_config = {"from_attributes": True}


class FacultyLogin(BaseModel):
    """Schema for login requests."""

    email: str
    password: str

