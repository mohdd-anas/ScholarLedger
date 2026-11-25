"""Test health endpoints."""


class TestHealthEndpoints:
    def test_healthz(self, client):
        response = client.get("/healthz")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_readyz(self, client):
        response = client.get("/readyz")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"

    def test_metrics(self, client):
        response = client.get("/metrics")
        assert response.status_code == 200

    def test_root(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert "ScholarLedger" in response.text

