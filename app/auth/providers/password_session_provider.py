"""Provider that authenticates a browser via the ``lavs_session`` cookie."""

import duckdb
from fastapi import Request

from app.auth.auth_provider import AuthProvider
from app.auth.principal import Principal
from app.auth.principal_kind import PrincipalKind
from app.auth.session.session_cookie import SessionCookie
from app.auth.session.session_service import SessionService
from app.auth.users.user_repository import UserRepository


class PasswordSessionProvider(AuthProvider):
    """Authenticate a request by its ``lavs_session`` session cookie.

    Reads the cookie, looks up a live (unexpired) session by the token's hash,
    and — on a hit — mints a ``user`` principal for the owning account. On any
    miss (no cookie, unknown/expired session, vanished user, or no live
    database) it returns ``None`` so another provider, or the resolver's 401,
    decides the request. It never raises for the not-me case.
    """

    def __init__(
        self,
        edition: str,
        session_service: SessionService | None = None,
        user_repository: UserRepository | None = None,
    ) -> None:
        """Initialise the provider.

        Args:
            edition: The edition stamped onto the resolved user principal.
            session_service: The session store. Defaults to a fresh
                :class:`~app.auth.session.session_service.SessionService`.
            user_repository: The user store. Defaults to a fresh
                :class:`~app.auth.users.user_repository.UserRepository`.
        """
        self._edition = edition
        self._session_service = session_service if session_service is not None else SessionService()
        self._user_repository = user_repository if user_repository is not None else UserRepository()

    async def authenticate(self, request: Request) -> Principal | None:
        """Authenticate the request via its session cookie.

        Args:
            request: The incoming request.

        Returns:
            A ``user`` principal when the cookie names a live session for an
            existing user, otherwise ``None``.
        """
        token = request.cookies.get(SessionCookie.NAME)
        if token is None or token == "":
            return None

        connection: duckdb.DuckDBPyConnection | None = request.app.state.db_connection
        if connection is None:
            return None

        user_id = self._session_service.lookup_active_user_id(connection, token)
        if user_id is None:
            return None

        user_row = await self._user_repository.get_user_by_id(connection, user_id)
        if user_row is None:
            return None

        return Principal(
            kind=PrincipalKind.USER,
            id=user_id,
            email=str(user_row[1]),
            edition=self._edition,
        )
