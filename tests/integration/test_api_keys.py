"""Integration tests for API key generation, authentication, and revocation."""

from app.auth.security import generate_api_key, hash_password
from app.models.api_key import ApiKey
from app.models.faculty import Faculty, FacultyRole


class TestApiKeys:
    def test_create_and_use_api_key(self, client, db_session):
        fac = Faculty(
            name="API User",
            email="api.user@university.edu",
            department="Computer Science",
            role=FacultyRole.FACULTY,
            password_hash=hash_password("password123!"),
        )
        db_session.add(fac)
        db_session.flush()

        # Login via session and create API key via UI endpoint
        client.post(
            "/login",
            data={"email": "api.user@university.edu", "password": "password123!"},
            follow_redirects=False,
        )
        resp = client.post(
            "/api-keys/create",
            data={"name": "CI Script Key"},
            follow_redirects=False,
        )
        assert resp.status_code == 302

        # Check DB stored hashed key
        stored = db_session.query(ApiKey).filter(ApiKey.faculty_id == fac.id).first()
        assert stored is not None
        assert stored.name == "CI Script Key"
        assert stored.is_active is True

    def test_x_api_key_auth_and_revoke(self, client, db_session):
        fac = Faculty(
            name="Key Tester",
            email="key.tester@university.edu",
            department="Physics",
            role=FacultyRole.VIEWER,
            password_hash=hash_password("password123!"),
        )
        db_session.add(fac)
        db_session.flush()

        plaintext, prefix, key_hash = generate_api_key()
        api_key = ApiKey(
            name="Test Token",
            key_prefix=prefix,
            key_hash=key_hash,
            faculty_id=fac.id,
            is_active=True,
        )
        db_session.add(api_key)
        db_session.flush()

        # Valid key succeeds without session cookie
        res = client.get("/api/v1/me", headers={"X-API-Key": plaintext})
        assert res.status_code == 200
        assert res.json()["email"] == "key.tester@university.edu"

        res_pubs = client.get("/api/v1/publications", headers={"X-API-Key": plaintext})
        assert res_pubs.status_code == 200

        # Invalid key fails
        bad = client.get("/api/v1/me", headers={"X-API-Key": "pb1_invalid_token"})
        assert bad.status_code == 401

        # Revoke key and verify rejection
        api_key.is_active = False
        db_session.flush()
        revoked = client.get("/api/v1/me", headers={"X-API-Key": plaintext})
        assert revoked.status_code == 401
