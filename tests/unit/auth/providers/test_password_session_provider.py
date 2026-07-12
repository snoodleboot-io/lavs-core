"""Unit tests for :class:`PasswordSessionProvider`."""

from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase

import duckdb
from fastapi import Request

from app.auth.principal_kind import PrincipalKind
from app.auth.providers.password_session_provider import PasswordSessionProvider
from app.auth.session.session_cookie import SessionCookie
from app.auth.session.session_service import SessionService
from app.auth.users.user_repository import UserRepository
from app.auth.users.user_status import UserStatus
from app.database.database_manager import DatabaseManager
from app.models.types.ulid_id import new_ulid


def _request(conn: duckdb.DuckDBPyConnection | None, cookie: str | None) -> Request:
    """Build a request whose ``app.state.db_connection`` is ``conn``.

    Args:
        conn: The connection to expose on ``app.state`` (or ``None``).
        cookie: The raw ``lavs_session`` cookie value, or ``None`` for no cookie.

    Returns:
        A request carrying the given cookie and application state.
    """
    headers: list[tuple[bytes, bytes]] = []
    if cookie is not None:
        headers.append((b"cookie", f"{SessionCookie.NAME}={cookie}".encode()))
    app = SimpleNamespace(state=SimpleNamespace(db_connection=conn))
    scope = {"type": "http", "method": "GET", "path": "/", "headers": headers, "app": app}
    return Request(scope)


class TestPasswordSessionProvider(IsolatedAsyncioTestCase):
    """Cookie-based session authentication."""

    def setUp(self) -> None:
        """Open an in-memory DuckDB, install the schema, and seed a user."""
        self._conn = duckdb.connect(":memory:")
        DatabaseManager.create_tables_on(self._conn)
        self._sessions = SessionService()
        self._provider = PasswordSessionProvider(edition="oss")
        self._user_id = new_ulid()

    def tearDown(self) -> None:
        """Close the in-memory connection."""
        self._conn.close()

    async def _seed_user(self) -> None:
        await UserRepository().create_user(
            self._conn,
            user_id=self._user_id,
            email="engineer@example.com",
            password_hash="$argon2id$fake",
            status=UserStatus.ACTIVE,
            edition="oss",
        )

    async def test_valid_cookie_returns_user_principal(self) -> None:
        """A cookie naming a live session resolves to a user principal."""
        # Arrange
        await self._seed_user()
        token = self._sessions.create_session(self._conn, user_id=self._user_id, ttl_seconds=3600)
        request = _request(self._conn, token)

        # Act
        principal = await self._provider.authenticate(request)

        # Assert
        assert principal is not None
        assert principal.kind is PrincipalKind.USER
        assert principal.id == self._user_id
        assert principal.email == "engineer@example.com"
        assert principal.edition == "oss"

    async def test_missing_cookie_returns_none(self) -> None:
        """No session cookie means the provider declines the request."""
        # Arrange
        request = _request(self._conn, None)

        # Act / Assert
        assert await self._provider.authenticate(request) is None

    async def test_unknown_token_returns_none(self) -> None:
        """A cookie with no matching session resolves to None."""
        # Arrange
        request = _request(self._conn, "not-a-real-token")

        # Act / Assert
        assert await self._provider.authenticate(request) is None

    async def test_expired_session_returns_none(self) -> None:
        """An expired session cookie authenticates nobody."""
        # Arrange
        await self._seed_user()
        token = self._sessions.create_session(self._conn, user_id=self._user_id, ttl_seconds=-1)
        request = _request(self._conn, token)

        # Act / Assert
        assert await self._provider.authenticate(request) is None

    async def test_no_database_connection_returns_none(self) -> None:
        """With no live connection the provider declines rather than raises."""
        # Arrange
        request = _request(None, "any-token")

        # Act / Assert
        assert await self._provider.authenticate(request) is None
