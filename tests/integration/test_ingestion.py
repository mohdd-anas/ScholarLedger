"""Integration tests for ingestion, scholar import, metrics, and CSV export."""

from app.auth.security import hash_password
from app.models.faculty import Faculty, FacultyRole
from app.models.publication import Publication, PublicationSource, PublicationStatus
from app.services.ingestion.scholar_import import parse_bibtex, parse_csv_export
from app.services.metrics import (
    compute_coverage,
    compute_duplicate_rate,
    compute_sync_reliability,
)
from app.services.sync_service import ingest_works_for_faculty


class TestScholarImportAndSync:
    def test_parse_bibtex(self):
        bib = """@article{smith2024deep,
  title = {Deep Learning for Citation Analysis},
  author = {Smith, Alice and Johnson, Bob},
  journal = {Journal of Informetrics},
  year = {2024},
  doi = {10.1016/j.joi.2024.001}
}"""
        works = parse_bibtex(bib)
        assert len(works) == 1
        assert works[0]["title"] == "Deep Learning for Citation Analysis"
        assert works[0]["year"] == 2024
        assert works[0]["doi"] == "10.1016/j.joi.2024.001"
        assert works[0]["source"] == "scholar_export"

    def test_parse_csv(self):
        csv_data = (
            "Title,Authors,Year,Venue,DOI\n"
            "Quantum Algorithms,Bob J.,2023,PRL,10.1103/prl.2023.1\n"
        )
        works = parse_csv_export(csv_data)
        assert len(works) == 1
        assert works[0]["title"] == "Quantum Algorithms"
        assert works[0]["year"] == 2023
        assert works[0]["doi"] == "10.1103/prl.2023.1"

    def test_ingest_works_for_faculty(self, db_session):
        fac = Faculty(
            name="Dr. Alice",
            email="alice.ingest@university.edu",
            department="CS",
            orcid_id="0000-0001-9999-8888",
            role=FacultyRole.FACULTY,
            password_hash=hash_password("password123!"),
        )
        db_session.add(fac)
        db_session.flush()

        works = [
            {
                "title": "Automated Pipeline Security",
                "authors": "Alice",
                "year": 2024,
                "doi": "10.1145/sec.2024.1",
                "type": "conference-paper",
                "source": "orcid",
            },
            {
                "title": "Automated Pipeline Security",
                "authors": "Alice",
                "year": 2024,
                "doi": "10.1145/sec.2024.1",
                "type": "conference-paper",
                "source": "openalex",
            },
        ]
        fetched, merged, queued = ingest_works_for_faculty(db_session, fac, works, "orcid")
        assert fetched == 2
        assert merged == 1
        assert queued == 0

        stored = db_session.query(Publication).filter(
            Publication.owner_faculty_id == fac.id
        ).all()
        assert len(stored) == 1
        assert stored[0].doi == "10.1145/sec.2024.1"

    def test_ingest_shared_doi_attributes_coauthor(self, db_session):
        fac_a = Faculty(
            name="Dr. First Author",
            email="first.shared@university.edu",
            department="CS",
            orcid_id="0000-0001-1111-2222",
            role=FacultyRole.FACULTY,
            password_hash=hash_password("password123!"),
        )
        fac_b = Faculty(
            name="Dr. Second Author",
            email="second.shared@university.edu",
            department="ECE",
            orcid_id="0000-0002-3333-4444",
            role=FacultyRole.FACULTY,
            password_hash=hash_password("password123!"),
        )
        db_session.add_all([fac_a, fac_b])
        db_session.flush()

        shared_work = [
            {
                "title": "Cross-Departmental ML Systems",
                "authors": "First Author; Second Author",
                "year": 2025,
                "doi": "https://doi.org/10.1145/shared.2025.1",
                "type": "conference-paper",
                "source": "openalex",
            }
        ]
        ingest_works_for_faculty(db_session, fac_a, shared_work, "openalex")
        fetched, merged, queued = ingest_works_for_faculty(
            db_session, fac_b, shared_work, "openalex"
        )
        assert fetched == 1
        assert merged == 1
        assert queued == 0

        pubs = db_session.query(Publication).filter(
            Publication.doi == "10.1145/shared.2025.1"
        ).all()
        assert len(pubs) == 1
        assert pubs[0].owner_faculty_id == fac_a.id
        assert pubs[0].coauthor_ids == [fac_b.id]
        assert pubs[0].is_attributed_to(fac_b.id)

        # Re-syncing for the co-author remains idempotent
        _, merged_again, queued_again = ingest_works_for_faculty(
            db_session, fac_b, shared_work, "openalex"
        )
        assert merged_again == 1
        assert queued_again == 0
        assert pubs[0].coauthor_ids == [fac_b.id]

    def test_metrics_and_csv_export(self, client, db_session):
        viewer = Faculty(
            name="IQAC Viewer",
            email="iqac.test@university.edu",
            department="IQAC",
            role=FacultyRole.VIEWER,
            password_hash=hash_password("viewer123!"),
        )
        db_session.add(viewer)
        db_session.flush()

        pub = Publication(
            title="Verified Metric Paper",
            authors="IQAC",
            year=2024,
            department="CS",
            status=PublicationStatus.VERIFIED,
            source=PublicationSource.CROSSREF,
            owner_faculty_id=viewer.id,
        )
        db_session.add(pub)
        db_session.flush()

        cov = compute_coverage(db_session)
        assert cov["total"] >= 1
        assert compute_duplicate_rate(db_session) == 0.0
        assert compute_sync_reliability(db_session) == 0.0

        client.post(
            "/login",
            data={"email": "iqac.test@university.edu", "password": "viewer123!"},
            follow_redirects=False,
        )
        resp = client.get("/reports/export/csv")
        assert resp.status_code == 200
        assert "Verified Metric Paper" in resp.text
