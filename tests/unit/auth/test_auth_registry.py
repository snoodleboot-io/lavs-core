"""Unit tests for :class:`AuthRegistry`."""

from fastapi import Request

from app.auth.auth_provider import AuthProvider
from app.auth.auth_registry import AuthRegistry
from app.auth.principal import Principal


class _StubProvider(AuthProvider):
    """A provider that never authenticates (identity is irrelevant here)."""

    async def authenticate(self, request: Request) -> Principal | None:
        return None


class TestAuthRegistry:
    """Registration order and emptiness."""

    def test_new_registry_is_empty(self) -> None:
        """A fresh registry reports empty and yields no providers."""
        # Arrange
        registry = AuthRegistry()

        # Act / Assert
        assert registry.is_empty() is True
        assert registry.providers() == ()

    def test_preserves_registration_order(self) -> None:
        """Providers are returned in the order they were registered."""
        # Arrange
        registry = AuthRegistry()
        first = _StubProvider()
        second = _StubProvider()

        # Act
        registry.register(first)
        registry.register(second)

        # Assert
        assert registry.is_empty() is False
        assert registry.providers() == (first, second)
