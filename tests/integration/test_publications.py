"""Integration tests for publication routes."""

import pytest

from app.auth.security import hash_password
from app.models.faculty import Faculty, FacultyRole
from app.models.publication import Publication


class TestPublicationRoutes:
    @pytest.fixture
    def logged_in_client(self, client, db_session):
        """Create a user and log them in."""
        user = Faculty(
            name="Test Faculty",
            email="faculty@university.edu",
            department="Computer Science",
            role=FacultyRole.FACULTY,
            password_hash=hash_password("password123!"),
        )
        db_session.add(user)
        db_session.flush()

        # Login via session
        client.post(
            "/login",
            data={"email": "faculty@university.edu", "password": "password123!"},
            follow_redirects=False,
        )
        return client

    def test_publications_requires_auth(self, client):
        response = client.get("/publications")
        assert response.status_code in [401, 403, 302]

    def test_create_publication(self, logged_in_client, db_session):
        response = logged_in_client.post(
            "/publications/new",
            data={
                "title": "Test Publication",
                "authors": "Faculty, T.",
                "venue": "Test Journal",
                "year": "2024",
                "doi": "10.1234/test.001",
                "pub_type": "journal-article",
                "department": "Computer Science",
            },
            follow_redirects=False,
        )
        assert response.status_code == 302

    def test_coauthor_attribution_and_permissions(self, client, db_session):
        owner = Faculty(
            name="Owner Prof",
            email="owner.prof@university.edu",
            department="Computer Science",
            role=FacultyRole.FACULTY,
            password_hash=hash_password("password123!"),
        )
        coauthor = Faculty(
            name="Coauthor Prof",
            email="coauthor.prof@university.edu",
            department="Mathematics",
            role=FacultyRole.FACULTY,
            password_hash=hash_password("password123!"),
        )
        db_session.add_all([owner, coauthor])
        db_session.flush()

        # Owner creates publication with coauthor selected
        client.post(
            "/login",
            data={"email": "owner.prof@university.edu", "password": "password123!"},
            follow_redirects=False,
        )
        resp = client.post(
            "/publications/new",
            data={
                "title": "Joint Research Paper",
                "authors": "Owner Prof; Coauthor Prof",
                "venue": "Joint Journal",
                "year": "2025",
                "doi": "10.1234/joint.2025",
                "pub_type": "journal-article",
                "department": "Computer Science",
                "coauthor_ids": [str(coauthor.id)],
            },
            follow_redirects=False,
        )
        assert resp.status_code == 302
        pub = db_session.query(Publication).filter(
            Publication.doi == "10.1234/joint.2025"
        ).first()
        assert pub is not None
        assert pub.coauthor_ids == [coauthor.id]

        # Co-author logs in and can view list, detail, and API JSON, but not edit
        client.post("/logout", follow_redirects=False)
        client.post(
            "/login",
            data={"email": "coauthor.prof@university.edu", "password": "password123!"},
            follow_redirects=False,
        )

        list_resp = client.get("/publications")
        assert list_resp.status_code == 200
        assert "Joint Research Paper" in list_resp.text
        assert "Co-author" in list_resp.text

        detail_resp = client.get(f"/publications/{pub.id}")
        assert detail_resp.status_code == 200
        assert "Coauthor Prof" in detail_resp.text

        api_resp = client.get("/api/v1/publications")
        assert api_resp.status_code == 200
        payload = api_resp.json()
        assert len(payload) == 1
        assert payload[0]["coauthor_ids"] == [coauthor.id]

        edit_resp = client.post(
            f"/publications/{pub.id}/edit",
            data={"title": "Hijacked Title", "authors": "Coauthor Prof"},
            follow_redirects=False,
        )
        assert edit_resp.status_code == 403

        # Department report in co-author's department includes the shared paper
        report_resp = client.get("/reports?department=Mathematics")
        assert report_resp.status_code == 200
        csv_resp = client.get("/reports/export/csv?department=Mathematics")
        assert csv_resp.status_code == 200
        assert "Joint Research Paper" in csv_resp.text
        assert "Coauthor Prof" in csv_resp.text

        # Co-author can remove themselves
        leave_resp = client.post(
            f"/publications/{pub.id}/coauthors/{coauthor.id}/remove",
            follow_redirects=False,
        )
        assert leave_resp.status_code == 302
        db_session.refresh(pub)
        assert pub.coauthor_ids == []
        assert client.get(f"/publications/{pub.id}").status_code == 403

        # Re-submitting the same DOI claims co-authorship instead of failing
        claim_resp = client.post(
            "/publications/new",
            data={
                "title": "Joint Research Paper",
                "authors": "Owner Prof; Coauthor Prof",
                "doi": "https://doi.org/10.1234/joint.2025",
            },
            follow_redirects=False,
        )
        assert claim_resp.status_code == 302
        db_session.refresh(pub)
        assert pub.coauthor_ids == [coauthor.id]

    def test_download_publication_proof_pdf(self, client, db_session):
        owner = Faculty(
            name="Proof Owner",
            email="proof.owner@university.edu",
            department="Computer Science",
            role=FacultyRole.FACULTY,
            password_hash=hash_password("password123!"),
        )
        coauthor = Faculty(
            name="Proof Coauthor",
            email="proof.coauthor@university.edu",
            department="Physics",
            role=FacultyRole.FACULTY,
            password_hash=hash_password("password123!"),
        )
        outsider = Faculty(
            name="Outsider Prof",
            email="outsider.prof@university.edu",
            department="Chemistry",
            role=FacultyRole.FACULTY,
            password_hash=hash_password("password123!"),
        )
        db_session.add_all([owner, coauthor, outsider])
        db_session.flush()

        pub = Publication(
            title="MXene–Transition Metal Piezoelectric Nanogenerators",
            authors="Owner, P.; Coauthor, P.",
            venue="ACS Applied Electronic Materials",
            year=2026,
            doi="10.1021/acsaelm.6c01064",
            department="Computer Science",
            owner_faculty_id=owner.id,
        )
        pub.coauthors.append(coauthor)
        db_session.add(pub)
        db_session.flush()

        # Owner can download PDF proof and detail page shows button
        client.post(
            "/login",
            data={"email": "proof.owner@university.edu", "password": "password123!"},
            follow_redirects=False,
        )
        detail = client.get(f"/publications/{pub.id}")
        assert detail.status_code == 200
        assert f"/publications/{pub.id}/proof" in detail.text
        assert "Download Proof (PDF)" in detail.text

        proof_resp = client.get(f"/publications/{pub.id}/proof")
        assert proof_resp.status_code == 200
        assert proof_resp.headers["content-type"] == "application/pdf"
        assert (
            f"scholarledger_publication_{pub.id}_proof.pdf"
            in proof_resp.headers["content-disposition"]
        )
        assert proof_resp.content.startswith(b"%PDF-1.4")
        assert b"%%EOF" in proof_resp.content
        assert b"10.1021/acsaelm.6c01064" in proof_resp.content
        assert b"Proof Coauthor" in proof_resp.content

        # Co-author can also download the proof
        client.post("/logout", follow_redirects=False)
        client.post(
            "/login",
            data={"email": "proof.coauthor@university.edu", "password": "password123!"},
            follow_redirects=False,
        )
        co_resp = client.get(f"/publications/{pub.id}/proof")
        assert co_resp.status_code == 200
        assert co_resp.content.startswith(b"%PDF-1.4")

        # Unrelated faculty cannot download
        client.post("/logout", follow_redirects=False)
        client.post(
            "/login",
            data={"email": "outsider.prof@university.edu", "password": "password123!"},
            follow_redirects=False,
        )
        denied_resp = client.get(f"/publications/{pub.id}/proof")
        assert denied_resp.status_code == 403

    def test_university_filter_on_publications_and_reports(self, client, db_session):
        admin = Faculty(
            name="Admin Uni",
            email="admin.uni@university.edu",
            department="Administration",
            university="UPES",
            role=FacultyRole.ADMIN,
            password_hash=hash_password("admin123!"),
        )
        fac_other = Faculty(
            name="Other Uni Prof",
            email="other.uni@university.edu",
            department="Computer Science",
            university="IIT Delhi",
            role=FacultyRole.FACULTY,
            password_hash=hash_password("password123!"),
        )
        db_session.add_all([admin, fac_other])
        db_session.flush()

        pub_upes = Publication(
            title="UPES Cloud Security Paper",
            authors="Admin Uni",
            department="Administration",
            university="UPES",
            owner_faculty_id=admin.id,
        )
        pub_iit = Publication(
            title="IIT Delhi Robotics Paper",
            authors="Other Uni Prof",
            department="Computer Science",
            university="IIT Delhi",
            owner_faculty_id=fac_other.id,
        )
        db_session.add_all([pub_upes, pub_iit])
        db_session.flush()

        client.post(
            "/login",
            data={"email": "admin.uni@university.edu", "password": "admin123!"},
            follow_redirects=False,
        )

        list_upes = client.get("/publications?university=UPES")
        assert list_upes.status_code == 200
        assert "UPES Cloud Security Paper" in list_upes.text
        assert "IIT Delhi Robotics Paper" not in list_upes.text

        report_iit = client.get("/reports?university=IIT+Delhi")
        assert report_iit.status_code == 200
        assert "IIT Delhi" in report_iit.text

        csv_upes = client.get("/reports/export/csv?university=UPES")
        assert csv_upes.status_code == 200
        assert "University" in csv_upes.text
        assert "UPES Cloud Security Paper" in csv_upes.text
        assert "IIT Delhi Robotics Paper" not in csv_upes.text

    def test_typeable_coauthor_input_links_faculty_or_adds_author(self, client, db_session):
        owner = Faculty(
            name="Owner Writer",
            email="owner.writer@university.edu",
            department="CS",
            role=FacultyRole.FACULTY,
            password_hash=hash_password("password123!"),
        )
        colleague = Faculty(
            name="Dr. Colleague",
            email="colleague@university.edu",
            department="CS",
            role=FacultyRole.FACULTY,
            password_hash=hash_password("password123!"),
        )
        db_session.add_all([owner, colleague])
        db_session.flush()

        pub = Publication(
            title="Typed Coauthor Test Paper",
            authors="Owner Writer",
            department="CS",
            owner_faculty_id=owner.id,
        )
        db_session.add(pub)
        db_session.flush()

        client.post(
            "/login",
            data={"email": "owner.writer@university.edu", "password": "password123!"},
            follow_redirects=False,
        )

        # 1. Typing registered faculty via autocomplete format links their Faculty account
        r1 = client.post(
            f"/publications/{pub.id}/coauthors/add",
            data={"coauthor_query": "Dr. Colleague (colleague@university.edu)"},
            follow_redirects=False,
        )
        assert r1.status_code == 302
        db_session.refresh(pub)
        assert pub.coauthor_ids == [colleague.id]

        # 2. Typing an unregistered co-author name appends it to Publication.authors
        r2 = client.post(
            f"/publications/{pub.id}/coauthors/add",
            data={"coauthor_query": "Dr. Hitesh Kumar Sharma"},
            follow_redirects=False,
        )
        assert r2.status_code == 302
        db_session.refresh(pub)
        assert "Dr. Hitesh Kumar Sharma" in pub.authors

        # Duplicate typed name is not appended twice
        client.post(
            f"/publications/{pub.id}/coauthors/add",
            data={"coauthor_query": "Dr. Hitesh Kumar Sharma"},
            follow_redirects=False,
        )
        db_session.refresh(pub)
        assert pub.authors.count("Dr. Hitesh Kumar Sharma") == 1
