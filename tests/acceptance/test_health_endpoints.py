"""Acceptance: liveness / readiness endpoints (P0 cross-cutting).

ROADMAP §5 cross-cutting: "``/health`` and ``/ready`` endpoints -- the Helm probes in
``helm/lavs`` need real targets." API_CONTRACT.md §3 lists
``GET /health`` / ``GET /ready`` as liveness/readiness probes.

Both must return 200. Until these endpoints are implemented they will 404 (RED).
"""

from fastapi.testclient import TestClient


class TestHealthEndpoints:
    """P0 exit criterion: health and readiness probes respond 200."""

    def test_health_returns_200(self, client: TestClient) -> None:
        """``GET /health`` returns 200 (liveness probe target)."""
        response = client.get("/health")

        assert response.status_code == 200, (
            f"GET /health must return 200; got {response.status_code}: {response.text}"
        )

    def test_ready_returns_200(self, client: TestClient) -> None:
        """``GET /ready`` returns 200 (readiness probe target)."""
        response = client.get("/ready")

        assert response.status_code == 200, (
            f"GET /ready must return 200; got {response.status_code}: {response.text}"
        )
