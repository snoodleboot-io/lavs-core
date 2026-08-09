"""Unit tests for :class:`ApiKeyProvider`."""

from unittest import IsolatedAsyncioTestCase

from fastapi import Request

from app.auth.principal_kind import PrincipalKind
from app.auth.providers.api_key_provider import ApiKeyProvider
from app.auth.service_identity import ServiceIdentity
from app.security.api_key import API_KEY_ENV_VAR, API_KEY_HEADER


def _request_with_headers(headers: dict[str, str]) -> Request:
    """Build a request carrying the given headers."""
    raw = [(key.lower().encode(), value.encode()) for key, value in headers.items()]
    scope = {"type": "http", "method": "GET", "path": "/", "headers": raw}
    return Request(scope)


class TestApiKeyProvider(IsolatedAsyncioTestCase):
    """Header-based API-key authentication."""

    def setUp(self) -> None:
        """Record and clear the API-key environment variable."""
        import os

        self._os = os
        self._saved = os.environ.get(API_KEY_ENV_VAR)
        os.environ.pop(API_KEY_ENV_VAR, None)
        self._provider = ApiKeyProvider(edition="oss")

    def tearDown(self) -> None:
        """Restore the API-key environment variable."""
        if self._saved is None:
            self._os.environ.pop(API_KEY_ENV_VAR, None)
        else:
            self._os.environ[API_KEY_ENV_VAR] = self._saved

    async def test_no_configured_key_returns_none(self) -> None:
        """With no key configured the provider declines every request."""
        # Arrange
        request = _request_with_headers({API_KEY_HEADER: "anything"})

        # Act / Assert
        assert await self._provider.authenticate(request) is None

    async def test_matching_key_returns_service_principal(self) -> None:
        """A correct key yields the ``api-key`` service principal."""
        # Arrange
        self._os.environ[API_KEY_ENV_VAR] = "top-secret"
        request = _request_with_headers({API_KEY_HEADER: "top-secret"})

        # Act
        principal = await self._provider.authenticate(request)

        # Assert
        assert principal is not None
        assert principal.kind is PrincipalKind.SERVICE
        assert principal.id == ServiceIdentity.API_KEY.value
        assert principal.edition == "oss"

    async def test_wrong_key_returns_none(self) -> None:
        """An incorrect key is not authenticated."""
        # Arrange
        self._os.environ[API_KEY_ENV_VAR] = "top-secret"
        request = _request_with_headers({API_KEY_HEADER: "guess"})

        # Act / Assert
        assert await self._provider.authenticate(request) is None

    async def test_missing_header_returns_none(self) -> None:
        """A configured key with no header present is not authenticated."""
        # Arrange
        self._os.environ[API_KEY_ENV_VAR] = "top-secret"
        request = _request_with_headers({})

        # Act / Assert
        assert await self._provider.authenticate(request) is None
