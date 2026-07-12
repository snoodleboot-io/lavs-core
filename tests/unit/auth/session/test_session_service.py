"""Unit tests for :class:`SessionService` against an in-memory database."""

from unittest import IsolatedAsyncioTestCase

import duckdb

from app.auth.session.session_service import SessionService
from app.auth.token_service import TokenService
from app.auth.users.user_repository import UserRepository
from app.auth.users.user_status import UserStatus
from app.database.database_manager import DatabaseManager
from app.models.types.ulid_id import new_ulid


class TestSessionService(IsolatedAsyncioTestCase):
    """Create, look up, and revoke session tokens."""

    def setUp(self) -> None:
        """Open an in-memory DuckDB, install the schema, and seed a user."""
        self._conn = duckdb.connect(":memory:")
        DatabaseManager.create_tables_on(self._conn)
        self._service = SessionService()
        self._tokens = TokenService()
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

    async def test_create_session_stores_hashed_token_not_raw(self) -> None:
        """The stored row carries the token's hash, never the raw token."""
        # Arrange
        await self._seed_user()

        # Act
        token = self._service.create_session(self._conn, user_id=self._user_id, ttl_seconds=3600)

        # Assert
        row = self._conn.execute(
            "SELECT user_id, token_hash FROM sessions WHERE user_id = ?", [self._user_id]
        ).fetchone()
        assert row is not None
        assert row[0] == self._user_id
        assert row[1] == self._tokens.hash_token(token)
        assert row[1] != token

    async def test_create_session_sets_future_expiry(self) -> None:
        """A positive TTL produces an ``expires_at`` in the future."""
        # Arrange
        await self._seed_user()

        # Act
        self._service.create_session(self._conn, user_id=self._user_id, ttl_seconds=3600)

        # Assert
        row = self._conn.execute(
            "SELECT expires_at > CURRENT_TIMESTAMP FROM sessions WHERE user_id = ?",
            [self._user_id],
        ).fetchone()
        assert row is not None
        assert row[0] is True

    async def test_lookup_active_returns_user_id(self) -> None:
        """A live session resolves to its owning user id."""
        # Arrange
        await self._seed_user()
        token = self._service.create_session(self._conn, user_id=self._user_id, ttl_seconds=3600)

        # Act
        result = self._service.lookup_active_user_id(self._conn, token)

        # Assert
        assert result == self._user_id

    async def test_lookup_unknown_token_returns_none(self) -> None:
        """A token with no session row resolves to None."""
        # Act
        result = self._service.lookup_active_user_id(self._conn, "no-such-token")

        # Assert
        assert result is None

    async def test_lookup_expired_session_returns_none(self) -> None:
        """A session whose expiry has passed no longer authenticates."""
        # Arrange
        await self._seed_user()
        token = self._service.create_session(self._conn, user_id=self._user_id, ttl_seconds=-1)

        # Act
        result = self._service.lookup_active_user_id(self._conn, token)

        # Assert
        assert result is None

    async def test_delete_session_revokes_lookup(self) -> None:
        """Deleting a session makes its token stop resolving."""
        # Arrange
        await self._seed_user()
        token = self._service.create_session(self._conn, user_id=self._user_id, ttl_seconds=3600)

        # Act
        self._service.delete_session(self._conn, token)

        # Assert
        assert self._service.lookup_active_user_id(self._conn, token) is None

    async def test_delete_unknown_token_is_noop(self) -> None:
        """Deleting a non-existent session raises nothing (idempotent)."""
        # Act / Assert
        self._service.delete_session(self._conn, "no-such-token")
