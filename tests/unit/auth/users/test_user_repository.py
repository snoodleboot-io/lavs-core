"""Unit tests for :class:`UserRepository` against an in-memory database."""

from unittest import IsolatedAsyncioTestCase

import duckdb

from app.auth.users.user_repository import UserRepository
from app.auth.users.user_status import UserStatus
from app.database.database_manager import DatabaseManager
from app.models.responses.user_response_model import UserResponseModel
from app.models.types.ulid_id import new_ulid


class TestUserRepository(IsolatedAsyncioTestCase):
    """Create, read, and activate users."""

    def setUp(self) -> None:
        """Open an in-memory DuckDB and install the real schema."""
        self._conn = duckdb.connect(":memory:")
        DatabaseManager.create_tables_on(self._conn)
        self._repo = UserRepository()

    def tearDown(self) -> None:
        """Close the in-memory connection."""
        self._conn.close()

    async def _create(self, email: str) -> UserResponseModel:
        return await self._repo.create_user(
            self._conn,
            user_id=new_ulid(),
            email=email,
            password_hash="$argon2id$fake",
            status=UserStatus.PENDING,
            edition="oss",
        )

    async def test_create_user_returns_safe_model(self) -> None:
        """Creation returns a response model that never carries the hash."""
        # Act
        result = await self._create("engineer@example.com")

        # Assert
        assert isinstance(result, UserResponseModel)
        assert result.email == "engineer@example.com"
        assert result.status == UserStatus.PENDING.value
        assert "password_hash" not in result.model_dump()

    async def test_get_user_by_email_returns_row_with_hash(self) -> None:
        """Lookup by email returns the raw row including the password hash."""
        # Arrange
        await self._create("lookup@example.com")

        # Act
        row = await self._repo.get_user_by_email(self._conn, "lookup@example.com")

        # Assert
        assert row is not None
        assert row[1] == "lookup@example.com"
        assert row[2] == "$argon2id$fake"

    async def test_get_user_by_email_unknown_returns_none(self) -> None:
        """An unknown email yields None."""
        # Act / Assert
        assert await self._repo.get_user_by_email(self._conn, "nobody@example.com") is None

    async def test_get_user_by_id_round_trips(self) -> None:
        """A created user is retrievable by its id."""
        # Arrange
        created = await self._create("byid@example.com")

        # Act
        row = await self._repo.get_user_by_id(self._conn, created.id)

        # Assert
        assert row is not None
        assert row[0] == created.id

    async def test_activate_user_sets_active_status(self) -> None:
        """Activation transitions a pending user to active."""
        # Arrange
        created = await self._create("activate@example.com")

        # Act
        await self._repo.activate_user(self._conn, created.id)

        # Assert
        row = await self._repo.get_user_by_id(self._conn, created.id)
        assert row is not None
        assert row[3] == UserStatus.ACTIVE.value

    async def test_duplicate_email_is_rejected(self) -> None:
        """The UNIQUE(email) constraint rejects a second user with same email."""
        # Arrange
        await self._create("dupe@example.com")

        # Act / Assert
        with self.assertRaises(duckdb.ConstraintException):
            await self._create("dupe@example.com")
