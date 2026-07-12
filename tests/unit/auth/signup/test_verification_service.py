"""Unit tests for :class:`VerificationService` against an in-memory database."""

from unittest import IsolatedAsyncioTestCase

import duckdb

from app.auth.signup.verification_service import VerificationService
from app.auth.signup.verification_token_repository import VerificationTokenRepository
from app.auth.token_service import TokenService
from app.auth.users.user_repository import UserRepository
from app.auth.users.user_status import UserStatus
from app.database.database_manager import DatabaseManager
from app.errors.not_found_error import NotFoundError
from app.models.requests.verify_model import VerifyModel
from app.models.responses.user_response_model import UserResponseModel
from app.models.types.ulid_id import new_ulid


class TestVerificationService(IsolatedAsyncioTestCase):
    """Activation, single-use consumption, and generic failure on a bad token."""

    def setUp(self) -> None:
        """Open an in-memory DuckDB, install schema, seed a pending user + token."""
        self._conn = duckdb.connect(":memory:")
        DatabaseManager.create_tables_on(self._conn)
        self._tokens = VerificationTokenRepository()
        self._token_service = TokenService()
        self._service = VerificationService()
        self._user_id = new_ulid()
        self._raw_token = self._token_service.generate_token()

    def tearDown(self) -> None:
        """Close the in-memory connection."""
        self._conn.close()

    async def _seed(self, ttl_seconds: int = 3600) -> None:
        await UserRepository().create_user(
            self._conn,
            user_id=self._user_id,
            email="engineer@example.com",
            password_hash="$argon2id$fake",
            status=UserStatus.PENDING,
            edition="oss",
        )
        await self._tokens.issue(
            self._conn,
            token_hash=self._token_service.hash_token(self._raw_token),
            user_id=self._user_id,
            ttl_seconds=ttl_seconds,
        )

    async def test_verify_activates_user_and_returns_model(self) -> None:
        """A valid token activates the user and returns the safe model."""
        # Arrange
        await self._seed()

        # Act
        result = await self._service.verify(self._conn, VerifyModel(token=self._raw_token))

        # Assert
        assert isinstance(result, UserResponseModel)
        assert result.id == self._user_id
        assert result.status == UserStatus.ACTIVE.value
        assert "password_hash" not in result.model_dump()

    async def test_verify_is_single_use(self) -> None:
        """A second verification of the same token fails generically."""
        # Arrange
        await self._seed()
        await self._service.verify(self._conn, VerifyModel(token=self._raw_token))

        # Act / Assert
        with self.assertRaises(NotFoundError):
            await self._service.verify(self._conn, VerifyModel(token=self._raw_token))

    async def test_expired_token_fails(self) -> None:
        """An expired token cannot verify and leaves the user pending."""
        # Arrange
        await self._seed(ttl_seconds=-10)

        # Act / Assert
        with self.assertRaises(NotFoundError):
            await self._service.verify(self._conn, VerifyModel(token=self._raw_token))
        row = await UserRepository().get_user_by_id(self._conn, self._user_id)
        assert row is not None
        assert row[3] == UserStatus.PENDING.value

    async def test_unknown_token_fails(self) -> None:
        """A token that was never issued fails generically."""
        # Arrange
        await self._seed()

        # Act / Assert
        with self.assertRaises(NotFoundError):
            await self._service.verify(self._conn, VerifyModel(token="never-issued-token"))
