"""Unit tests for :class:`VerificationTokenRepository` over an in-memory DB."""

from unittest import IsolatedAsyncioTestCase

import duckdb

from app.auth.signup.verification_token_repository import VerificationTokenRepository
from app.auth.users.user_repository import UserRepository
from app.auth.users.user_status import UserStatus
from app.database.database_manager import DatabaseManager
from app.models.types.ulid_id import new_ulid


class TestVerificationTokenRepository(IsolatedAsyncioTestCase):
    """Issue, find (active only), and consume verification tokens."""

    def setUp(self) -> None:
        """Open an in-memory DuckDB, install the schema, seed a user."""
        self._conn = duckdb.connect(":memory:")
        DatabaseManager.create_tables_on(self._conn)
        self._repo = VerificationTokenRepository()
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
            status=UserStatus.PENDING,
            edition="oss",
        )

    async def test_issue_then_find_active_returns_row(self) -> None:
        """A freshly issued, unexpired token is found active."""
        # Arrange
        await self._seed_user()
        await self._repo.issue(self._conn, "hash-a", self._user_id, ttl_seconds=3600)

        # Act
        row = await self._repo.find_active(self._conn, "hash-a")

        # Assert
        assert row is not None
        assert row[1] == self._user_id

    async def test_expired_token_is_not_active(self) -> None:
        """A token issued with a negative TTL is already expired."""
        # Arrange
        await self._seed_user()
        await self._repo.issue(self._conn, "hash-expired", self._user_id, ttl_seconds=-10)

        # Act
        row = await self._repo.find_active(self._conn, "hash-expired")

        # Assert
        assert row is None

    async def test_consumed_token_is_not_active(self) -> None:
        """Consuming a token removes it from the active set (single-use)."""
        # Arrange
        await self._seed_user()
        await self._repo.issue(self._conn, "hash-b", self._user_id, ttl_seconds=3600)

        # Act
        await self._repo.consume(self._conn, "hash-b")

        # Assert
        assert await self._repo.find_active(self._conn, "hash-b") is None

    async def test_unknown_hash_is_not_active(self) -> None:
        """A hash that was never issued is never active."""
        # Act / Assert
        assert await self._repo.find_active(self._conn, "never-issued") is None
