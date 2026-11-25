"""Integration tests for the review queue."""

import pytest

from app.auth.security import hash_password
from app.models.faculty import Faculty, FacultyRole


class TestReviewQueue:
    @pytest.fixture
    def admin_client(self, client, db_session):
        """Create an admin user and log them in."""
        admin = Faculty(
            name="Admin User",
            email="admin@university.edu",
            department="Administration",
            role=FacultyRole.ADMIN,
            password_hash=hash_password("admin123!"),
        )
        db_session.add(admin)
        db_session.flush()

        client.post(
            "/login",
            data={"email": "admin@university.edu", "password": "admin123!"},
            follow_redirects=False,
        )
        return client, admin

    def test_review_queue_requires_admin(self, client):
        response = client.get("/review")
        assert response.status_code in [401, 403, 302]

    def test_review_queue_accessible_by_admin(self, admin_client, db_session):
        client, admin = admin_client
        response = client.get("/review")
        # Should work (200 or redirect to review page)
        assert response.status_code in [200, 302]
