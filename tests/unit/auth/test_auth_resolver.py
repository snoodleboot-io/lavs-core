"""Unit tests for :class:`AuthResolver` resolution semantics."""

from unittest import IsolatedAsyncioTestCase

from fastapi import Request

from app.auth.auth_registry import AuthRegistry
from app.auth.auth_resolver import AuthResolver
from app.auth.principal import Principal
from app.auth.principal_kind import PrincipalKind
from app.auth.service_identity import ServiceIdentity
from app.errors.unauthorized_error import UnauthorizedError


def _make_request() -> Request:
    """Build a minimal ASGI request (no header/app access is exercised here)."""
    scope = {"type": "http", "method": "GET", "path": "/", "headers": []}
    return Request(scope)


class _MatchingProvider:
    """A provider that always returns a fixed principal."""

    def __init__(self, principal: Principal) -> None:
        self._principal = principal

    async def authenticate(self, request: Request) -> Principal | None:
        return self._principal


class _NonMatchingProvider:
    """A provider that never authenticates."""

    async def authenticate(self, request: Request) -> Principal | None:
        return None


class TestAuthResolver(IsolatedAsyncioTestCase):
    """The single-principal-per-request resolution rules."""

    async def test_unconfigured_returns_anonymous(self) -> None:
        """No providers and auth not configured yields the anonymous principal."""
        # Arrange
        resolver = AuthResolver(AuthRegistry(), edition="oss", auth_configured=False)

        # Act
        principal = await resolver.resolve(_make_request())

        # Assert
        assert principal.kind is PrincipalKind.SERVICE
        assert principal.id == ServiceIdentity.ANONYMOUS.value
        assert principal.edition == "oss"

    async def test_configured_without_match_raises_401(self) -> None:
        """Auth configured but no provider matching raises Unauthorized."""
        # Arrange
        resolver = AuthResolver(AuthRegistry(), edition="oss", auth_configured=True)

        # Act / Assert
        with self.assertRaises(UnauthorizedError):
            await resolver.resolve(_make_request())

    async def test_first_matching_provider_wins(self) -> None:
        """The first provider to return a principal short-circuits resolution."""
        # Arrange
        expected = Principal(kind=PrincipalKind.USER, id="u1", edition="oss")
        registry = AuthRegistry()
        registry.register(_MatchingProvider(expected))
        resolver = AuthResolver(registry, edition="oss", auth_configured=True)

        # Act
        principal = await resolver.resolve(_make_request())

        # Assert
        assert principal is expected

    async def test_enabled_provider_that_declines_raises_401(self) -> None:
        """A registered provider that returns None still fails closed."""
        # Arrange
        registry = AuthRegistry()
        registry.register(_NonMatchingProvider())
        resolver = AuthResolver(registry, edition="oss", auth_configured=False)

        # Act / Assert
        with self.assertRaises(UnauthorizedError):
            await resolver.resolve(_make_request())

    async def test_registry_is_read_live(self) -> None:
        """A provider registered after construction is honoured on resolve."""
        # Arrange
        registry = AuthRegistry()
        resolver = AuthResolver(registry, edition="oss", auth_configured=True)
        expected = Principal(kind=PrincipalKind.USER, id="late", edition="oss")

        # Act — register only after the resolver already exists
        registry.register(_MatchingProvider(expected))
        principal = await resolver.resolve(_make_request())

        # Assert
        assert principal is expected
