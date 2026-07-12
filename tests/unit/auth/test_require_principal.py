"""Unit tests for the ``require_principal`` FastAPI dependency.

Exercised through a tiny app so the real request/``app.state`` plumbing is used:
one route echoes the resolved principal. Proves the two contract-critical paths
— open when nothing is configured (the backward-compat default), and fail-closed
(401) when a configured resolver is present on ``app.state``.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth.auth_mode import AuthMode
from app.auth.auth_resolver_factory import AuthResolverFactory
from app.auth.auth_settings import AuthSettings
from app.auth.require_principal import PrincipalDep
from app.errors.handlers import register_error_handlers


def _build_app() -> FastAPI:
    """Build a minimal app with one principal-protected route."""
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/whoami")
    async def whoami(principal: PrincipalDep) -> dict[str, str]:
        return {"kind": principal.kind.value, "id": principal.id}

    return app


class TestRequirePrincipalOpen:
    """With no resolver configured, requests resolve to the anonymous principal."""

    def test_open_when_unconfigured(self, monkeypatch) -> None:
        """A bare app (no lifespan, no env) stays open via the fallback resolver."""
        # Arrange
        monkeypatch.delenv("LAVS_AUTH_MODES", raising=False)
        monkeypatch.delenv("LAVS_API_KEY", raising=False)
        client = TestClient(_build_app())

        # Act
        response = client.get("/whoami")

        # Assert
        assert response.status_code == 200
        assert response.json() == {"kind": "service", "id": "anonymous"}


class TestRequirePrincipalFailClosed:
    """With a configured resolver on app.state, unauthenticated requests 401."""

    def test_fail_closed_when_configured(self, monkeypatch) -> None:
        """A password-configured resolver rejects a credential-less request."""
        # Arrange
        monkeypatch.delenv("LAVS_API_KEY", raising=False)
        app = _build_app()
        settings = AuthSettings(modes={AuthMode.PASSWORD})
        app.state.auth_resolver = AuthResolverFactory.build_resolver(settings)
        client = TestClient(app)

        # Act
        response = client.get("/whoami")

        # Assert
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthorized"
