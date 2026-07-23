"""Integration tests for the ``/auth/*`` per-IP rate limit on the real app.

Exercises the full stack (``app.main.app`` with its wired
``RateLimitMiddleware``): the limit is enabled through the environment before
requests are made — settings are read per request, so no restart is needed —
and the trusted ``X-Forwarded-For`` flag is switched on so each test can claim
a unique client IP. That keeps tests isolated from one another even though the
middleware instance (and its buckets) lives for the whole process.
"""

import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient


def _unique_ip() -> str:
    """Return a practically collision-free RFC1918 address for one test."""
    value = uuid.uuid4().int
    return f"10.{(value >> 16) & 255}.{(value >> 8) & 255}.{value & 255}"


@pytest.fixture()
def limited_client(test_db: str, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """Yield a lifespan-active client with a 3-request/hour limit enabled.

    API-key auth is also configured so a resource route can be exercised with
    a valid credential while the auth surface is throttled.
    """
    monkeypatch.setenv("LAVS_AUTH_RATE_LIMIT", "3")
    monkeypatch.setenv("LAVS_AUTH_RATE_WINDOW_SECONDS", "3600")
    monkeypatch.setenv("LAVS_AUTH_RATE_TRUST_FORWARDED_FOR", "true")
    monkeypatch.setenv("LAVS_AUTH_MODES", "password,apikey")
    monkeypatch.setenv("LAVS_API_KEY", "rate-limit-suite-key")

    from app.main import app

    with TestClient(app) as client:
        yield client


class TestAuthRateLimit:
    """The wired middleware throttles /auth/* per client IP."""

    def test_auth_route_returns_429_envelope_when_exhausted(
        self, limited_client: TestClient
    ) -> None:
        """The fourth login attempt from one IP is refused with the envelope."""
        # Arrange
        headers = {"X-Forwarded-For": _unique_ip()}
        body = {"email": "probe@example.com", "password": "wrong-password-123"}
        for _ in range(3):
            response = limited_client.post("/auth/login", json=body, headers=headers)
            assert response.status_code == 401

        # Act
        refused = limited_client.post("/auth/login", json=body, headers=headers)

        # Assert
        assert refused.status_code == 429
        payload = refused.json()
        assert payload["error"]["code"] == "rate_limited"
        assert payload["error"]["message"]
        assert payload["error"]["details"] == {"retry_after_seconds": 3600}
        assert refused.headers["Retry-After"] == "3600"

    def test_other_ip_keeps_its_own_budget(self, limited_client: TestClient) -> None:
        """Exhausting one IP leaves a different client unthrottled."""
        # Arrange
        exhausted = {"X-Forwarded-For": _unique_ip()}
        body = {"email": "probe@example.com", "password": "wrong-password-123"}
        for _ in range(3):
            limited_client.post("/auth/login", json=body, headers=exhausted)
        assert limited_client.post("/auth/login", json=body, headers=exhausted).status_code == 429

        # Act
        fresh = limited_client.post(
            "/auth/login", json=body, headers={"X-Forwarded-For": _unique_ip()}
        )

        # Assert — a fresh IP gets the normal (generic 401) auth answer.
        assert fresh.status_code == 401

    def test_resource_route_with_valid_key_is_never_limited(
        self, limited_client: TestClient
    ) -> None:
        """Only /auth/* is throttled: an authenticated resource route is not."""
        # Arrange — exhaust the auth budget for this IP first.
        headers = {"X-Forwarded-For": _unique_ip()}
        body = {"email": "probe@example.com", "password": "wrong-password-123"}
        for _ in range(3):
            limited_client.post("/auth/login", json=body, headers=headers)
        assert limited_client.post("/auth/login", json=body, headers=headers).status_code == 429

        # Act — hit a credentialed resource route well past the auth budget.
        responses = [
            limited_client.get(
                "/products",
                headers={"X-API-Key": "rate-limit-suite-key", **headers},
            )
            for _ in range(6)
        ]

        # Assert
        assert all(response.status_code == 200 for response in responses)
