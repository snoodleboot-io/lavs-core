"""Tests that every error surfaces as the uniform error envelope."""

from typing import Annotated

import pytest
from fastapi import FastAPI, HTTPException, Query
from fastapi.testclient import TestClient

from app.errors.conflict_error import ConflictError
from app.errors.error_code import ErrorCode
from app.errors.forbidden_error import ForbiddenError
from app.errors.handlers import register_error_handlers
from app.errors.not_found_error import NotFoundError


def _build_app() -> FastAPI:
    """Build a throwaway app whose routes raise each error kind."""
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/not-found")
    def _not_found() -> None:
        raise NotFoundError("missing thing", {"id": "abc"})

    @app.get("/conflict")
    def _conflict() -> None:
        raise ConflictError("already exists")

    @app.get("/validate")
    def _validate(value: Annotated[int, Query()]) -> dict[str, int]:
        return {"value": value}

    @app.get("/forbidden")
    def _forbidden() -> None:
        raise ForbiddenError("not permitted", {"resource": "release"})

    @app.get("/teapot")
    def _teapot() -> None:
        raise HTTPException(status_code=418, detail="i am a teapot")

    return app


@pytest.fixture()
def client() -> TestClient:
    """A ``TestClient`` over the throwaway error app."""
    return TestClient(_build_app(), raise_server_exceptions=False)


class TestDomainErrorEnvelopes:
    """Typed domain errors map to their status and envelope code."""

    def test_not_found_returns_404_envelope(self, client: TestClient) -> None:
        """``NotFoundError`` serializes as a 404 ``not_found`` envelope."""
        # Act
        response = client.get("/not-found")

        # Assert
        assert response.status_code == 404
        body = response.json()
        assert body["error"]["code"] == ErrorCode.NOT_FOUND.value
        assert body["error"]["message"] == "missing thing"
        assert body["error"]["details"] == {"id": "abc"}

    def test_conflict_returns_409_envelope(self, client: TestClient) -> None:
        """``ConflictError`` serializes as a 409 ``conflict`` envelope."""
        # Act
        response = client.get("/conflict")

        # Assert
        assert response.status_code == 409
        body = response.json()
        assert body["error"]["code"] == ErrorCode.CONFLICT.value
        assert body["error"]["message"] == "already exists"
        assert body["error"]["details"] == {}

    def test_forbidden_returns_403_envelope(self, client: TestClient) -> None:
        """``ForbiddenError`` serializes as a 403 ``forbidden`` envelope."""
        # Act
        response = client.get("/forbidden")

        # Assert
        assert response.status_code == 403
        body = response.json()
        assert body["error"]["code"] == ErrorCode.FORBIDDEN.value
        assert body["error"]["message"] == "not permitted"
        assert body["error"]["details"] == {"resource": "release"}


class TestFrameworkErrorEnvelopes:
    """Framework validation and HTTP errors map to the envelope too."""

    def test_validation_error_returns_422_envelope(self, client: TestClient) -> None:
        """A bad query parameter yields a 422 ``validation_error`` envelope."""
        # Act
        response = client.get("/validate?value=not-an-int")

        # Assert
        assert response.status_code == 422
        body = response.json()
        assert body["error"]["code"] == ErrorCode.VALIDATION_ERROR.value
        assert "errors" in body["error"]["details"]

    def test_http_exception_maps_to_envelope(self, client: TestClient) -> None:
        """A generic ``HTTPException`` is wrapped in the envelope."""
        # Act
        response = client.get("/teapot")

        # Assert
        assert response.status_code == 418
        body = response.json()
        assert body["error"]["code"] == ErrorCode.HTTP_ERROR.value
        assert body["error"]["message"] == "i am a teapot"
