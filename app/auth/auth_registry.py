"""An order-preserving registry of the enabled authentication providers."""

from app.auth.auth_provider import AuthProvider


class AuthRegistry:
    """Holds the enabled :class:`~app.auth.auth_provider.AuthProvider` instances.

    Registration order is preserved and is the order in which the resolver tries
    providers. The registry is mutable and lives on ``app.state`` so a later lane
    (R2's ``PasswordSessionProvider``) can register itself after the foundation
    has wired the API-key provider — the resolver reads the registry live, so a
    provider registered after the resolver was constructed still takes effect.
    """

    def __init__(self) -> None:
        """Initialise an empty registry."""
        self._providers: list[AuthProvider] = []

    def register(self, provider: AuthProvider) -> None:
        """Append a provider to the end of the try-order.

        Args:
            provider: The provider to enable.
        """
        self._providers.append(provider)

    def providers(self) -> tuple[AuthProvider, ...]:
        """Return the enabled providers in registration order."""
        return tuple(self._providers)

    def is_empty(self) -> bool:
        """Return ``True`` when no provider is enabled."""
        return not self._providers
