"""The provider abstraction every authentication mechanism implements."""

from abc import ABC, abstractmethod

from fastapi import Request

from app.auth.principal import Principal


class AuthProvider(ABC):
    """One authentication mechanism (API key, password/session, Stytch, ...).

    A provider inspects the incoming request and returns a
    :class:`~app.auth.principal.Principal` when it recognises the credential, or
    ``None`` when the request is simply "not for me". It must **never** raise for
    the not-me case — deciding whether an unauthenticated request is a 401 is the
    resolver's job, made once across all providers. See
    ``docs/design/API_CONTRACT.md`` §1.
    """

    @abstractmethod
    async def authenticate(self, request: Request) -> Principal | None:
        """Attempt to authenticate the request.

        Args:
            request: The incoming request to inspect for a credential.

        Returns:
            The resolved principal when this provider recognises and validates
            the credential, otherwise ``None``.
        """
        raise NotImplementedError
