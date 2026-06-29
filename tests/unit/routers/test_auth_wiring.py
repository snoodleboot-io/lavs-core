"""Unit tests verifying API-key authentication is wired onto data routers.

These tests confirm the behavior contract for the API-key dependency on the
data routers (versions, patch, basic_crud):

- When ``LAVS_API_KEY`` is set, a request without a valid ``X-API-Key`` header
  is rejected with HTTP 401, while a request with the correct key passes.
- When ``LAVS_API_KEY`` is unset, the routes stay open (no auth enforced).

The downstream query execution is stubbed out via monkeypatch so the tests do
not touch the database and exercise only the auth wiring.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers import basic_crud, patch, versions
from app.security.api_key import API_KEY_ENV_VAR, API_KEY_HEADER


def _build_app() -> FastAPI:
    """Build a minimal FastAPI app including the data routers."""
    app = FastAPI()
    app.include_router(patch.router)
    app.include_router(basic_crud.router)
    app.include_router(versions.router)
    return app


def _stub_queries(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stub query ``execute`` methods so no database access occurs.

    This isolates the tests to the auth wiring: any request that passes
    authentication reaches a handler whose query returns a benign value
    instead of hitting the real database.
    """
    from app.queries.crud.retrieve_all import RetrieveAll
    from app.queries.patch_version.read_current_patch import ReadCurrentPatch

    async def _empty_list(self: object, data: object) -> list[object]:
        return []

    async def _read_patch(self: object, data: object) -> dict[str, object]:
        return {"product_name": "x", "major": 1, "minor": 0, "patch": 0}

    monkeypatch.setattr(RetrieveAll, "execute", _empty_list, raising=True)
    monkeypatch.setattr(ReadCurrentPatch, "execute", _read_patch, raising=True)


class TestAuthWiringEnabled:
    """Behavior when ``LAVS_API_KEY`` is configured (auth enabled)."""

    def test_protected_route_rejected_without_header(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A request lacking ``X-API-Key`` is rejected with 401."""
        monkeypatch.setenv(API_KEY_ENV_VAR, "secret-key")
        client = TestClient(_build_app())

        response = client.get("/crud/read_all?product_name=test")

        assert response.status_code == 401

    def test_protected_route_passes_with_correct_header(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A request with the correct ``X-API-Key`` passes auth and succeeds."""
        monkeypatch.setenv(API_KEY_ENV_VAR, "secret-key")
        _stub_queries(monkeypatch)
        client = TestClient(_build_app())

        response = client.get(
            "/crud/read_all?product_name=test",
            headers={API_KEY_HEADER: "secret-key"},
        )

        assert response.status_code == 200

    def test_versions_route_rejected_without_header(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The versions router also enforces auth when enabled."""
        monkeypatch.setenv(API_KEY_ENV_VAR, "secret-key")
        client = TestClient(_build_app())

        response = client.get("/versions/?product_name=test")

        assert response.status_code == 401

    def test_patch_route_rejected_without_header(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The patch router also enforces auth when enabled."""
        monkeypatch.setenv(API_KEY_ENV_VAR, "secret-key")
        client = TestClient(_build_app())

        response = client.get("/patch/?product_name=test")

        assert response.status_code == 401


class TestAuthWiringDisabled:
    """Behavior when ``LAVS_API_KEY`` is unset (auth disabled / open)."""

    def test_route_open_when_api_key_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """With no configured key, the route stays open (no 401/403)."""
        monkeypatch.delenv(API_KEY_ENV_VAR, raising=False)
        _stub_queries(monkeypatch)
        client = TestClient(_build_app())

        response = client.get("/crud/read_all?product_name=test")

        assert response.status_code == 200
