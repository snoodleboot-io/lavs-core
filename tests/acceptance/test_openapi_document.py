"""Acceptance: the published OpenAPI document (P7 release polish).

The ``/openapi.json`` document is part of the release surface: it must carry
real app metadata (title, version from the installed ``lavs`` distribution)
and declare exactly the two auth schemes API_CONTRACT §1–2 ships in v1 — the
headless ``X-API-Key`` header and the ``lavs_session`` HttpOnly cookie. The
security markers must be honest: principal-guarded routes advertise both
schemes as alternatives, while the public bootstrap surface (``/health``,
``/ready``, ``/meta``, the credential-establishing ``/auth`` flows) carries no
requirement. The document is static and must never echo configured secrets.
"""

import importlib.metadata
import json

import pytest
from fastapi.testclient import TestClient

from app.auth.session.session_cookie import SessionCookie
from tests.acceptance._auth_support import API_KEY, auth_test_client


@pytest.fixture
def auth_client(monkeypatch, test_db: str):
    """A lifespan-active client with password + API-key auth both configured."""
    monkeypatch.setenv("LAVS_STYTCH_SECRET", "secret-key-test-not-for-openapi")
    with auth_test_client(monkeypatch, api_key=API_KEY) as client:
        yield client


@pytest.fixture
def openapi_document(auth_client: TestClient) -> dict:
    """The parsed ``/openapi.json`` document (asserted to return 200)."""
    response = auth_client.get("/openapi.json")
    assert response.status_code == 200, response.text
    return response.json()


class TestOpenApiDocument:
    """The document is served with release-grade metadata and auth schemes."""

    def test_openapi_json_returns_200(self, auth_client: TestClient) -> None:
        """``GET /openapi.json`` returns 200 with a JSON document."""
        # Act
        response = auth_client.get("/openapi.json")

        # Assert
        assert response.status_code == 200, response.text
        assert isinstance(response.json(), dict)

    def test_docs_returns_200(self, auth_client: TestClient) -> None:
        """``GET /docs`` (Swagger UI) renders against the document."""
        # Act
        response = auth_client.get("/docs")

        # Assert
        assert response.status_code == 200, response.text

    def test_info_title_and_version_are_populated(self, openapi_document: dict) -> None:
        """``info.title`` is LAVS and ``info.version`` is the installed version."""
        # Assert
        info = openapi_document["info"]
        assert info["title"] == "LAVS"
        assert info["version"], "info.version must be populated"
        assert info["version"] == importlib.metadata.version("lavs")
        assert info.get("description"), "info.description must be populated"

    def test_api_key_scheme_matches_contract(self, openapi_document: dict) -> None:
        """``apiKeyAuth`` is an apiKey scheme reading the X-API-Key header."""
        # Assert
        schemes = openapi_document["components"]["securitySchemes"]
        assert "apiKeyAuth" in schemes, f"missing apiKeyAuth; got {sorted(schemes)}"
        api_key_scheme = schemes["apiKeyAuth"]
        assert api_key_scheme["type"] == "apiKey"
        assert api_key_scheme["in"] == "header"
        assert api_key_scheme["name"] == "X-API-Key"

    def test_cookie_scheme_matches_contract(self, openapi_document: dict) -> None:
        """``cookieAuth`` is an apiKey scheme reading the session cookie."""
        # Assert
        schemes = openapi_document["components"]["securitySchemes"]
        assert "cookieAuth" in schemes, f"missing cookieAuth; got {sorted(schemes)}"
        cookie_scheme = schemes["cookieAuth"]
        assert cookie_scheme["type"] == "apiKey"
        assert cookie_scheme["in"] == "cookie"
        assert cookie_scheme["name"] == SessionCookie.NAME

    def test_document_contains_no_configured_secrets(self, openapi_document: dict) -> None:
        """Neither the configured API key nor the Stytch secret leaks into the doc."""
        # Act
        serialized = json.dumps(openapi_document)

        # Assert — the doc is static; configured credential values never appear
        assert API_KEY not in serialized
        assert "secret-key-test-not-for-openapi" not in serialized
        assert "LAVS_STYTCH_SECRET" not in serialized
        assert "LAVS_API_KEY" not in serialized


class TestOpenApiSecurityMarkers:
    """``security`` requirements mirror the real ``require_principal`` guards."""

    @pytest.mark.parametrize(
        "path",
        ["/health", "/ready", "/meta", "/auth/signup", "/auth/verify", "/auth/login"],
    )
    def test_public_routes_carry_no_security_requirement(
        self, openapi_document: dict, path: str
    ) -> None:
        """The public bootstrap surface is not marked as secured."""
        # Assert
        operations = openapi_document["paths"][path]
        for method, operation in operations.items():
            assert "security" not in operation, (
                f"{method.upper()} {path} is public and must not carry a security requirement"
            )

    @pytest.mark.parametrize(
        ("path", "method"),
        [("/products", "get"), ("/products", "post"), ("/auth/me", "get")],
    )
    def test_secured_routes_accept_either_scheme(
        self, openapi_document: dict, path: str, method: str
    ) -> None:
        """Principal-guarded routes list both schemes as alternatives."""
        # Assert
        operation = openapi_document["paths"][path][method]
        assert operation.get("security") == [{"apiKeyAuth": []}, {"cookieAuth": []}], (
            f"{method.upper()} {path} must accept either the API key or the session cookie"
        )
