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
