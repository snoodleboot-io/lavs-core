"""Unit tests for health and readiness endpoints.

These tests use FastAPI's TestClient (which drives the application lifespan)
to verify the liveness and readiness probes added in tickets #26/#27.
"""

from fastapi.testclient import TestClient

from app.main import app


class TestHealthEndpoints:
    """Test suite for the /health and /ready endpoints."""

    def test_health_returns_ok(self) -> None:
        """GET /health returns 200 with a status payload."""
        with TestClient(app) as client:
            response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_ready_returns_ok_when_db_answers(self) -> None:
        """GET /ready returns 200 when the managed DB answers SELECT 1."""
        with TestClient(app) as client:
            response = client.get("/ready")

        assert response.status_code == 200
        assert response.json() == {"status": "ready"}

    def test_root_still_available(self) -> None:
        """The existing GET / route is preserved."""
        with TestClient(app) as client:
            response = client.get("/")

        assert response.status_code == 200
