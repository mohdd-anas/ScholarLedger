"""Integration tests for auth endpoints."""

from app.models.faculty import Faculty


class TestAuthIntegration:
    def test_register_page(self, client):
        response = client.get("/register")
        assert response.status_code == 200
        assert "Create Account" in response.text

    def test_login_page(self, client):
        response = client.get("/login")
        assert response.status_code == 200
        assert "Login" in response.text

    def test_register_and_login(self, client, db_session):
        # Register
        response = client.post(
            "/register",
            data={
                "name": "Test User",
                "email": "test@university.edu",
                "department": "CS",
                "password": "password123!",
                "confirm_password": "password123!",
            },
            follow_redirects=False,
        )
        assert response.status_code == 302

        # Verify user was created
        user = db_session.query(Faculty).filter(Faculty.email == "test@university.edu").first()
        assert user is not None
        assert user.name == "Test User"

    def test_login_invalid_credentials(self, client):
        response = client.post(
            "/login",
            data={"email": "nobody@university.edu", "password": "wrongpassword"},
            follow_redirects=False,
        )
        assert response.status_code == 302  # Redirect back to login

    def test_logout(self, client):
        response = client.post("/logout", follow_redirects=False)
        assert response.status_code == 302
