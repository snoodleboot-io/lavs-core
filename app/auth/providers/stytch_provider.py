"""Provider that authenticates a request by its Stytch session credential."""

from fastapi import Request

from app.auth.auth_provider import AuthProvider
from app.auth.principal import Principal
from app.auth.principal_kind import PrincipalKind
from app.auth.stytch.stytch_verifier import StytchVerifier
from app.auth.users.user_repository import UserRepository
from app.auth.users.user_status import UserStatus
from app.connections.db_session import DbSession


class StytchProvider(AuthProvider):
    """Authenticate a request by a Stytch session token or session JWT (EE).

    Reads the credential from the cookies the Stytch frontend SDK maintains
    (``stytch_session_jwt`` preferred, ``stytch_session`` as fallback) and
    verifies it through the injected :class:`StytchVerifier` — an abstraction
    over the Stytch SDK so tests inject a fake and never touch the network.

    A verified Stytch identity is **not** trusted on its own: the provider
    resolves the mapped LAVS account by the Stytch-**verified** email (same
    trim/lower normalization as the callback route) through the
    :class:`UserRepository`, and mints a ``user`` principal only when that row
    exists **and** is ``active`` — carrying the LAVS user id and the row's
    email, never the raw Stytch id. This keeps a disabled LAVS user disabled
    and an unmapped Stytch user unauthenticated even when their Stytch session
    itself is valid. On any miss (no credential, invalid/expired token, an
    unconfigured verifier, no verified email, no mapped row, a non-active row,
    or no live database) it returns ``None`` so another provider, or the
    resolver's 401, decides the request. It never raises for the not-me case.

    Note the primary EE flow does not depend on this provider: the
    ``POST /auth/stytch/callback`` route exchanges the Stytch token for a
    normal ``lavs_session`` cookie, which the session-cookie provider then
    authenticates. This provider covers callers presenting the Stytch
    credential directly.
    """

    _SESSION_JWT_COOKIE: str = "stytch_session_jwt"
    _SESSION_TOKEN_COOKIE: str = "stytch_session"

    def __init__(
        self,
        edition: str,
        verifier: StytchVerifier,
        user_repository: UserRepository | None = None,
    ) -> None:
        """Initialise the provider.

        Args:
            edition: The edition stamped onto the resolved user principal.
            verifier: The Stytch verification seam (SDK-backed in production,
                a fake in tests).
            user_repository: The user store the verified email is resolved
                against. Defaults to a fresh
                :class:`~app.auth.users.user_repository.UserRepository`.
        """
        self._edition = edition
        self._verifier = verifier
        self._user_repository = user_repository if user_repository is not None else UserRepository()

    async def authenticate(self, request: Request) -> Principal | None:
        """Authenticate the request via its Stytch session cookie.

        Args:
            request: The incoming request.

        Returns:
            A ``user`` principal when a presented Stytch credential verifies
            **and** maps onto an ``active`` LAVS user by its verified email,
            otherwise ``None``.
        """
        token = request.cookies.get(self._SESSION_JWT_COOKIE)
        if token is None or token == "":
            token = request.cookies.get(self._SESSION_TOKEN_COOKIE)
        if token is None or token == "":
            return None

        verification = await self._verifier.verify(token)
        if verification is None:
            return None
        if verification.email is None or not verification.email.strip():
            return None
        email = verification.email.strip().lower()

        connection: DbSession | None = request.app.state.db_connection
        if connection is None:
            return None

        user_row = await self._user_repository.get_user_by_email(connection, email)
        if user_row is None:
            return None
        if str(user_row[3]) != UserStatus.ACTIVE.value:
            return None

        return Principal(
            kind=PrincipalKind.USER,
            id=str(user_row[0]),
            email=str(user_row[1]),
            edition=self._edition,
        )
