"""Builds the auth registry and resolver from deployment settings.

Centralising construction here keeps the wiring identical between the
application lifespan (which stores the registry/resolver on ``app.state``) and
the request-time fallback in :mod:`app.auth.require_principal` (used when no
lifespan has run, e.g. a bare ``TestClient``). The API-key provider is enabled
when a key is configured (``is_authentication_enabled``) or the ``apikey`` mode
is explicitly listed in ``LAVS_AUTH_MODES``.
"""

from app.auth.auth_registry import AuthRegistry
from app.auth.auth_resolver import AuthResolver
from app.auth.auth_settings import AuthSettings
from app.auth.providers.api_key_provider import ApiKeyProvider
from app.security.api_key import is_authentication_enabled


class AuthResolverFactory:
    """Constructs the enabled-provider registry and its resolver."""

    @staticmethod
    def build_registry(settings: AuthSettings) -> AuthRegistry:
        """Build a registry populated with the providers enabled by ``settings``.

        Args:
            settings: The deployment auth settings.

        Returns:
            A registry holding every provider the foundation enables. R2 extends
            this by registering its password/session provider onto the returned
            registry (typically via ``app.state.auth_registry``).
        """
        registry = AuthRegistry()

        apikey_enabled = is_authentication_enabled() or settings.apikey_mode_enabled()
        if apikey_enabled:
            registry.register(ApiKeyProvider(edition=settings.edition()))

        return registry

    @staticmethod
    def build_resolver(
        settings: AuthSettings, registry: AuthRegistry | None = None
    ) -> AuthResolver:
        """Build a resolver over a registry (constructing one when not supplied).

        Args:
            settings: The deployment auth settings.
            registry: An existing registry to resolve over; when ``None`` a fresh
                registry is built from ``settings``.

        Returns:
            A resolver reading the (live) registry.
        """
        resolved_registry = (
            registry if registry is not None else AuthResolverFactory.build_registry(settings)
        )
        auth_configured = bool(settings.modes()) or is_authentication_enabled()
        return AuthResolver(
            registry=resolved_registry,
            edition=settings.edition(),
            auth_configured=auth_configured,
        )
