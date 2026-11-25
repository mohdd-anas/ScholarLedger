"""Seed the database with sample data for development."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.auth.security import hash_password  # noqa: E402
from app.database import Base, get_engine, get_session_factory  # noqa: E402
from app.models import (  # noqa: E402
    Faculty,
    FacultyRole,
    Publication,
    PublicationSource,
    PublicationStatus,
    PublicationType,
)


def seed():
    """Create sample faculty and publications."""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    session_factory = get_session_factory()
    session = session_factory()

    if session.query(Faculty).first():
        print("Database already seeded. Skipping.")
        return

    admin = Faculty(
        name="Dr. Admin User",
        email="admin@university.edu",
        department="Administration",
        role=FacultyRole.ADMIN,
        password_hash=hash_password("admin123!"),
    )
    faculty1 = Faculty(
        name="Dr. Alice Smith",
        email="alice@university.edu",
        department="Computer Science",
        orcid_id="0000-0001-2345-6789",
        role=FacultyRole.FACULTY,
        password_hash=hash_password("password123!"),
    )
    faculty2 = Faculty(
        name="Dr. Bob Johnson",
        email="bob@university.edu",
        department="Physics",
        orcid_id="0000-0002-3456-7890",
        role=FacultyRole.FACULTY,
        password_hash=hash_password("password123!"),
    )
    viewer = Faculty(
        name="IQAC Office",
        email="iqac@university.edu",
        department="Quality Assurance",
        role=FacultyRole.VIEWER,
        password_hash=hash_password("viewer123!"),
    )

    session.add_all([admin, faculty1, faculty2, viewer])
    session.flush()

    pubs = [
        Publication(
            title="Deep Learning for Natural Language Processing: A Survey",
            authors="Smith, A.; Johnson, B.",
            venue="ACM Computing Surveys",
            year=2024,
            doi="10.1145/1234567",
            pub_type=PublicationType.JOURNAL_ARTICLE,
            department="Computer Science",
            status=PublicationStatus.VERIFIED,
            source=PublicationSource.ORCID,
            owner_faculty_id=faculty1.id,
            match_confidence=1.0,
        ),
        Publication(
            title="Quantum Computing: Current State and Future Directions",
            authors="Johnson, B.; Smith, A.",
            venue="Physical Review Letters",
            year=2023,
            doi="10.1103/PhysRevLett.130.012345",
            pub_type=PublicationType.JOURNAL_ARTICLE,
            department="Physics",
            status=PublicationStatus.SUBMITTED,
            source=PublicationSource.OPENALEX,
            owner_faculty_id=faculty2.id,
            match_confidence=0.92,
        ),
        Publication(
            title="A Novel Approach to Graph Neural Networks",
            authors="Smith, A.",
            venue="NeurIPS 2024",
            year=2024,
            pub_type=PublicationType.CONFERENCE_PAPER,
            department="Computer Science",
            status=PublicationStatus.DRAFT,
            source=PublicationSource.MANUAL,
            owner_faculty_id=faculty1.id,
        ),
    ]
    session.add_all(pubs)
    session.commit()
    num_faculty = len([admin, faculty1, faculty2, viewer])
    print(f"Seeded {num_faculty} faculty and {len(pubs)} publications.")


if __name__ == "__main__":
    seed()

