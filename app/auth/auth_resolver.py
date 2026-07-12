"""Resolves a single principal per request across the enabled providers."""

from fastapi import Request

from app.auth.auth_registry import AuthRegistry
from app.auth.principal import Principal
from app.auth.principal_kind import PrincipalKind
from app.auth.service_identity import ServiceIdentity
from app.errors.unauthorized_error import UnauthorizedError


class AuthResolver:
    """Turns an enabled-provider registry into a single resolved principal.

    Semantics (see ``docs/design/API_CONTRACT.md`` §1):

    * **Auth not configured** — no auth mode selected and no API key set — return
      a permissive anonymous ``service`` principal so an unconfigured deployment
      (and the default test-suite) stays open. This is the backward-compatible
      path.
    * **Auth configured** — try each enabled provider in registration order and
      return the first principal produced. If none match, the request carried no
      valid credential and :class:`UnauthorizedError` (401) is raised.

    ``auth_configured`` is the fail-closed signal and is deliberately **not** the
    same as "the registry is non-empty": a mode can be configured before its
    provider is wired (for example ``LAVS_AUTH_MODES=password`` while R2's
    ``PasswordSessionProvider`` has not shipped). In that window every request
    fails closed (401) rather than silently falling open. The registry is read
    live on every resolve, so a provider registered after this resolver was
    constructed (e.g. R2's provider) is honoured without rebuilding the resolver.
    """

    def __init__(self, registry: AuthRegistry, edition: str, auth_configured: bool) -> None:
        """Initialise the resolver.

        Args:
            registry: The registry of enabled providers to consult.
            edition: The edition stamped onto the anonymous principal.
            auth_configured: Whether any authentication is configured for this
                deployment (an auth mode is selected or an API key is set). When
                ``True`` the resolver fails closed on an unauthenticated request.
        """
        self._registry = registry
        self._edition = edition
        self._auth_configured = auth_configured

    async def resolve(self, request: Request) -> Principal:
        """Resolve the caller's principal for a request.

        Args:
            request: The incoming request.

        Returns:
            The resolved principal (an anonymous service principal when auth is
            not configured).

        Raises:
            UnauthorizedError: When auth is configured but no provider
                authenticates the request.
        """
        providers = self._registry.providers()

        for provider in providers:
            principal = await provider.authenticate(request)
            if principal is not None:
                return principal

        if self._auth_configured or providers:
            raise UnauthorizedError(message="No valid credentials were provided.")

        return self._anonymous_principal()

    def _anonymous_principal(self) -> Principal:
        """Build the permissive anonymous principal used when auth is off."""
        return Principal(
            kind=PrincipalKind.SERVICE,
            id=ServiceIdentity.ANONYMOUS.value,
            edition=self._edition,
        )
