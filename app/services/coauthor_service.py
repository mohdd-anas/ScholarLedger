"""Shared helpers for internal faculty co-author attribution and queries."""

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.faculty import Faculty
from app.models.publication import Publication


def attributed_to_faculty_filter(faculty_id: int):
    """Return a filter matching publications owned or co-authored by a faculty member."""
    return or_(
        Publication.owner_faculty_id == faculty_id,
        Publication.coauthors.any(Faculty.id == faculty_id),
    )


def department_publication_filter(department: str):
    """Return a filter matching publications in a department or co-authored by its faculty."""
    return or_(
        Publication.department == department,
        Publication.coauthors.any(Faculty.department == department),
    )


def attribute_coauthor(publication: Publication, faculty: Faculty) -> bool:
    """Link a faculty member as an internal co-author if not already attributed."""
    if publication.is_attributed_to(faculty.id):
        return False
    publication.coauthors.append(faculty)
    return True


def sync_coauthors(
    db: Session,
    publication: Publication,
    raw_ids: list[str] | list[int],
) -> None:
    """Replace internal co-authors on a publication from submitted faculty IDs."""
    parsed_ids: list[int] = []
    for raw in raw_ids:
        try:
            fid = int(raw)
        except (TypeError, ValueError):
            continue
        if fid != publication.owner_faculty_id and fid not in parsed_ids:
            parsed_ids.append(fid)

    if not parsed_ids:
        publication.coauthors = []
        return

    publication.coauthors = (
        db.query(Faculty)
        .filter(Faculty.id.in_(parsed_ids))
        .order_by(Faculty.name)
        .all()
    )
