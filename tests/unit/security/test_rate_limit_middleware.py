"""Unit tests for :class:`RateLimitMiddleware` over a throwaway app."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.errors.error_code import ErrorCode
from app.security.rate_limit_middleware import RateLimitMiddleware
from app.security.rate_limit_settings import RateLimitSettings


def _build_client(settings: RateLimitSettings) -> TestClient:
    """Build a client over a minimal app with the middleware installed.

    Args:
        settings: The injected (environment-free) rate-limit settings.

    Returns:
        A ``TestClient`` whose app has one ``/auth/*`` route and one
        non-auth route.
    """
    app = FastAPI()

    @app.post("/auth/ping")
    def _auth_ping() -> dict[str, bool]:
        return {"ok": True}

    @app.get("/other/ping")
    def _other_ping() -> dict[str, bool]:
        return {"ok": True}

    app.add_middleware(RateLimitMiddleware, settings=settings)
    return TestClient(app)


class TestScopeAndDisabledMode:
    """The middleware only ever touches enabled ``/auth/*`` traffic."""

    def test_disabled_settings_never_limit(self) -> None:
        """With a zero limit every /auth request passes through."""
        # Arrange
        client = _build_client(RateLimitSettings(limit=0, window_seconds=60))

        # Act
        responses = [client.post("/auth/ping") for _ in range(10)]

        # Assert
        assert all(response.status_code == 200 for response in responses)

    def test_non_auth_paths_are_never_limited(self) -> None:
        """A tiny budget on /auth leaves other paths completely alone."""
        # Arrange
        client = _build_client(RateLimitSettings(limit=1, window_seconds=3600))
        assert client.post("/auth/ping").status_code == 200
        assert client.post("/auth/ping").status_code == 429

        # Act
        responses = [client.get("/other/ping") for _ in range(5)]

        # Assert
        assert all(response.status_code == 200 for response in responses)


class TestRefusal:
    """Over-budget requests get the enveloped 429."""

    def test_429_carries_error_envelope_and_retry_after(self) -> None:
        """The refusal body is the uniform envelope with code rate_limited."""
        # Arrange
        client = _build_client(RateLimitSettings(limit=1, window_seconds=45))
        assert client.post("/auth/ping").status_code == 200

        # Act
        response = client.post("/auth/ping")

        # Assert
        assert response.status_code == 429
        body = response.json()
        assert body["error"]["code"] == ErrorCode.RATE_LIMITED.value
        assert body["error"]["message"]
        assert body["error"]["details"] == {"retry_after_seconds": 45}
        assert response.headers["Retry-After"] == "45"


class TestClientIpExtraction:
    """Bucketing key selection with and without the forwarded-for flag."""

    def test_forwarded_for_ignored_by_default(self) -> None:
        """Without the trust flag, forged X-Forwarded-For cannot reset budgets."""
        # Arrange — every TestClient request shares the same transport peer.
        client = _build_client(RateLimitSettings(limit=2, window_seconds=3600))

        # Act — rotate forged addresses; the transport peer is still the key.
        first = client.post("/auth/ping", headers={"X-Forwarded-For": "1.1.1.1"})
        second = client.post("/auth/ping", headers={"X-Forwarded-For": "2.2.2.2"})
        third = client.post("/auth/ping", headers={"X-Forwarded-For": "3.3.3.3"})

        # Assert
        assert first.status_code == 200
        assert second.status_code == 200
        assert third.status_code == 429

    def test_forwarded_for_used_when_trusted(self) -> None:
        """With the flag on, each forwarded address owns its own budget."""
        # Arrange
        client = _build_client(
            RateLimitSettings(limit=1, window_seconds=3600, trust_forwarded_for=True)
        )

        # Act
        first_a = client.post("/auth/ping", headers={"X-Forwarded-For": "9.9.9.1"})
        second_a = client.post("/auth/ping", headers={"X-Forwarded-For": "9.9.9.1"})
        first_b = client.post("/auth/ping", headers={"X-Forwarded-For": "9.9.9.2"})

        # Assert
        assert first_a.status_code == 200
        assert second_a.status_code == 429
        assert first_b.status_code == 200

    def test_leftmost_forwarded_address_wins(self) -> None:
        """A proxy chain header buckets on the original (leftmost) client."""
        # Arrange
        client = _build_client(
            RateLimitSettings(limit=1, window_seconds=3600, trust_forwarded_for=True)
        )

        # Act
        first = client.post("/auth/ping", headers={"X-Forwarded-For": "8.8.8.8, 10.0.0.1"})
        second = client.post("/auth/ping", headers={"X-Forwarded-For": "8.8.8.8, 10.0.0.2"})

        # Assert — same leftmost client, so the second request is refused.
        assert first.status_code == 200
        assert second.status_code == 429

    def test_trusted_but_absent_header_falls_back_to_peer(self) -> None:
        """With trust on but no header, the transport peer is still limited."""
        # Arrange
        client = _build_client(
            RateLimitSettings(limit=1, window_seconds=3600, trust_forwarded_for=True)
        )

        # Act
        first = client.post("/auth/ping")
        second = client.post("/auth/ping")

        # Assert
        assert first.status_code == 200
        assert second.status_code == 429


class TestRuntimeToggle:
    """Settings are read per request, so env changes apply immediately."""

    def test_env_enable_takes_effect_without_restart(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """An environment-backed settings object toggles limiting live."""
        # Arrange
        monkeypatch.delenv("LAVS_AUTH_RATE_LIMIT", raising=False)
        monkeypatch.delenv("LAVS_AUTH_RATE_WINDOW_SECONDS", raising=False)
        client = _build_client(RateLimitSettings())
        assert client.post("/auth/ping").status_code == 200
        assert client.post("/auth/ping").status_code == 200

        # Act
        monkeypatch.setenv("LAVS_AUTH_RATE_LIMIT", "1")
        first_limited = client.post("/auth/ping")
        second_limited = client.post("/auth/ping")

        # Assert
        assert first_limited.status_code == 200
        assert second_limited.status_code == 429
