"""Acceptance: the public ``GET /meta`` capability endpoint (API_CONTRACT §1, §8).

``/meta`` is what the UI reads *before* a principal exists to decide which login
to render, so it must be reachable with no credentials even on a fully-configured
deployment, and it must advertise the edition and the enabled auth modes. This
suite configures ``password,apikey`` and asserts both modes surface and that the
edition is ``oss`` — and that the endpoint needs no auth.

``/meta`` ships with the foundation, so these scenarios are expected to pass now.
"""

import pytest
from fastapi.testclient import TestClient

from tests.acceptance._auth_support import API_KEY, auth_test_client


@pytest.fixture
def auth_client(monkeypatch, test_db: str):
    """A lifespan-active client with password + API-key auth both configured."""
    with auth_test_client(monkeypatch, api_key=API_KEY) as client:
        yield client


class TestMeta:
    """The capability descriptor is public and reflects the configured modes."""

    def test_meta_reports_oss_edition_and_enabled_modes(self, auth_client: TestClient) -> None:
        """``GET /meta`` returns 200 with edition ``oss`` and the enabled modes."""
        # Act
        response = auth_client.get("/meta")

        # Assert
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["edition"] == "oss"
        assert isinstance(body["auth_modes"], list)
        assert set(body["auth_modes"]) >= {"password", "apikey"}

    def test_meta_requires_no_authentication(self, auth_client: TestClient) -> None:
        """``/meta`` stays public even with providers configured and no credentials."""
        # Act — no cookie, no API key, yet auth is configured on this deployment
        response = auth_client.get("/meta")

        # Assert
        assert response.status_code == 200, response.text
