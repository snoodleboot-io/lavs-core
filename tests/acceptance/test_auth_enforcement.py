"""Acceptance: resource routes fail closed once auth is configured (API_CONTRACT §1).

Proves the ``require_principal`` gate on a representative resource route
(``GET /products``): with providers configured, a credential-less request is
rejected 401, while the *same* request carrying a valid credential succeeds 200.
Two credential kinds are exercised — the headless ``X-API-Key`` (works today via
the foundation's API-key provider) and the browser ``lavs_session`` cookie
minted by login (R2). A wrong API key is rejected, confirming the gate is not
merely presence-checking a header.

The API-key and unauthenticated scenarios pass against the current foundation;
the session-cookie scenario depends on the R2 login lane and is expected RED
until it merges.
"""

import pytest
from fastapi.testclient import TestClient

from tests.acceptance._auth_support import (
    API_KEY,
    assert_error_envelope,
    auth_test_client,
    login,
    signup_and_verify,
    unique_email,
)

_RESOURCE_ROUTE = "/products"


@pytest.fixture
def auth_client(monkeypatch, test_db: str):
    """A lifespan-active client with password + API-key auth both configured."""
    with auth_test_client(monkeypatch, api_key=API_KEY) as client:
        yield client


class TestResourceEnforcement:
    """A configured deployment rejects anonymous access and admits valid credentials."""

    def test_unauthenticated_request_is_rejected(self, auth_client: TestClient) -> None:
        """With auth configured, a credential-less resource request is 401."""
        # Act
        response = auth_client.get(_RESOURCE_ROUTE)

        # Assert
        assert response.status_code == 401, response.text
        assert_error_envelope(response.json(), "unauthorized")

    def test_valid_api_key_grants_access(self, auth_client: TestClient) -> None:
        """The configured ``X-API-Key`` authenticates a headless request 200."""
        # Act
        response = auth_client.get(_RESOURCE_ROUTE, headers={"X-API-Key": API_KEY})

        # Assert
        assert response.status_code == 200, response.text
        assert isinstance(response.json(), list)

    def test_wrong_api_key_is_rejected(self, auth_client: TestClient) -> None:
        """A non-matching ``X-API-Key`` is rejected 401 (not merely header-present)."""
        # Act
        response = auth_client.get(_RESOURCE_ROUTE, headers={"X-API-Key": "not-the-key"})

        # Assert
        assert response.status_code == 401, response.text
        assert_error_envelope(response.json(), "unauthorized")

    def test_valid_session_cookie_grants_access(self, auth_client: TestClient) -> None:
        """A logged-in user's session cookie authenticates the same resource route 200."""
        # Arrange
        email = unique_email()
        signup_and_verify(auth_client, email)
        assert login(auth_client, email).status_code == 200

        # Act — the client replays the session cookie from login automatically
        response = auth_client.get(_RESOURCE_ROUTE)

        # Assert
        assert response.status_code == 200, response.text
        assert isinstance(response.json(), list)
