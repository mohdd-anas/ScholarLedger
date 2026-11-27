"""Shared helpers for internal faculty co-author attribution and queries."""

import re

from sqlalchemy import func, or_
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


def university_publication_filter(university: str):
    """Return a filter matching publications for a university via pub, owner, or co-authors."""
    return or_(
        Publication.university == university,
        Publication.owner.has(Faculty.university == university),
        Publication.coauthors.any(Faculty.university == university),
    )


def get_distinct_universities(db: Session) -> list[str]:
    """Return sorted distinct non-empty university names across publications and faculty."""
    pub_unis = {r[0] for r in db.query(Publication.university).distinct().all() if r[0]}
    fac_unis = {r[0] for r in db.query(Faculty.university).distinct().all() if r[0]}
    return sorted(pub_unis | fac_unis)


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


def find_faculty_by_input(db: Session, raw_query: str) -> Faculty | None:
    """Resolve a typed name, email, or 'Name (email)' string to a registered Faculty."""
    query = raw_query.strip()
    if not query:
        return None

    email_match = re.search(r"\(([^()]+@[^()]+)\)$", query)
    if email_match:
        email = email_match.group(1).strip().lower()
        fac = db.query(Faculty).filter(func.lower(Faculty.email) == email).first()
        if fac:
            return fac

    fac_by_email = db.query(Faculty).filter(func.lower(Faculty.email) == query.lower()).first()
    if fac_by_email:
        return fac_by_email

    return db.query(Faculty).filter(func.lower(Faculty.name) == query.lower()).first()


def append_author_name(publication: Publication, author_name: str) -> bool:
    """Append an author name to Publication.authors if not already listed."""
    clean = author_name.strip()
    if not clean:
        return False

    existing_parts = [p.strip() for p in (publication.authors or "").split(";") if p.strip()]
    if any(part.lower() == clean.lower() for part in existing_parts):
        return False

    existing_parts.append(clean)
    publication.authors = "; ".join(existing_parts)
    return True
