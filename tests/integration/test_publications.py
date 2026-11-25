"""Integration tests for publication routes."""

import pytest

from app.auth.security import hash_password
from app.models.faculty import Faculty, FacultyRole


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
