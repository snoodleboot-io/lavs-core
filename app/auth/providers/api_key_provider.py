"""Provider that authenticates the headless ``X-API-Key`` credential."""

import hmac

from fastapi import Request

from app.auth.auth_provider import AuthProvider
from app.auth.principal import Principal
from app.auth.principal_kind import PrincipalKind
from app.auth.service_identity import ServiceIdentity
from app.security.api_key import API_KEY_HEADER, get_configured_api_key


class ApiKeyProvider(AuthProvider):
    """Authenticate a request by its ``X-API-Key`` header.

    Wraps the existing :mod:`app.security.api_key` configuration: it reads the
    header name and configured key from there and compares them with a
    constant-time comparison (:func:`hmac.compare_digest`) so a wrong key cannot
    be discovered by timing. On a match it mints a ``service`` principal; on any
    mismatch (or no configured key, or no header) it returns ``None`` and lets
    another provider — or the resolver's 401 — decide the request.
    """

    def __init__(self, edition: str) -> None:
        """Initialise the provider.

        Args:
            edition: The edition stamped onto the resolved service principal.
        """
        self._edition = edition

    async def authenticate(self, request: Request) -> Principal | None:
        """Authenticate the request via its API-key header.

        Args:
            request: The incoming request.

        Returns:
            A ``service`` principal when the header matches the configured key,
            otherwise ``None``.
        """
        configured_key = get_configured_api_key()
        if configured_key is None or configured_key == "":
            return None

        presented_key = request.headers.get(API_KEY_HEADER)
        if presented_key is None:
            return None

        if not hmac.compare_digest(presented_key, configured_key):
            return None

        return Principal(
            kind=PrincipalKind.SERVICE,
            id=ServiceIdentity.API_KEY.value,
            edition=self._edition,
        )
