"""Unit tests for :class:`SignupService` against an in-memory database."""

from unittest import IsolatedAsyncioTestCase

import duckdb

from app.auth.auth_settings import AuthSettings
from app.auth.password_hasher import PasswordHasher
from app.auth.signup.signup_service import SignupService
from app.auth.signup.verification_settings import VerificationSettings
from app.auth.token_service import TokenService
from app.auth.users.user_repository import UserRepository
from app.auth.users.user_status import UserStatus
from app.database.database_manager import DatabaseManager
from app.errors.conflict_error import ConflictError
from app.errors.domain_not_allowed_error import DomainNotAllowedError
from app.mail.capture_mailer import CaptureMailer
from app.models.requests.signup_model import SignupModel


class TestSignupService(IsolatedAsyncioTestCase):
    """Domain allow-list, duplicate handling, password + token hashing."""

    _PASSWORD: str = "correct horse battery staple"

    def setUp(self) -> None:
        """Open an in-memory DuckDB and install the real schema."""
        self._conn = duckdb.connect(":memory:")
        DatabaseManager.create_tables_on(self._conn)
        self._mailer = CaptureMailer()
        self._service = SignupService(verification_settings=VerificationSettings(ttl_seconds=3600))

    def tearDown(self) -> None:
        """Close the in-memory connection."""
        self._conn.close()

    def _body(self, email: str = "engineer@example.com") -> SignupModel:
        return SignupModel(email=email, password=self._PASSWORD)

    async def _register(self, settings: AuthSettings, email: str = "engineer@example.com") -> None:
        await self._service.register(
            conn=self._conn, mailer=self._mailer, model=self._body(email), settings=settings
        )

    async def test_open_allow_list_accepts_any_domain(self) -> None:
        """An empty allow-list permits sign-up from any domain."""
        # Arrange
        settings = AuthSettings(allowed_email_domains=())

        # Act
        await self._register(settings)

        # Assert
        row = await UserRepository().get_user_by_email(self._conn, "engineer@example.com")
        assert row is not None

    async def test_allowed_domain_is_accepted(self) -> None:
        """A domain present on the allow-list is accepted."""
        # Arrange
        settings = AuthSettings(allowed_email_domains=("example.com",))

        # Act
        await self._register(settings)

        # Assert
        assert self._mailer.last_for("engineer@example.com") is not None

    async def test_disallowed_domain_is_rejected(self) -> None:
        """A domain absent from a non-empty allow-list raises 403 and stores nothing."""
        # Arrange
        settings = AuthSettings(allowed_email_domains=("allowed.com",))

        # Act / Assert
        with self.assertRaises(DomainNotAllowedError):
            await self._register(settings, email="engineer@example.com")
        assert await UserRepository().get_user_by_email(self._conn, "engineer@example.com") is None
        assert self._mailer.messages() == ()

    async def test_duplicate_email_raises_conflict(self) -> None:
        """A second sign-up for the same email raises a conflict."""
        # Arrange
        settings = AuthSettings(allowed_email_domains=())
        await self._register(settings)

        # Act / Assert
        with self.assertRaises(ConflictError):
            await self._register(settings)

    async def test_password_is_stored_hashed(self) -> None:
        """The stored password differs from plaintext yet verifies."""
        # Arrange
        settings = AuthSettings(allowed_email_domains=())

        # Act
        await self._register(settings)

        # Assert
        row = await UserRepository().get_user_by_email(self._conn, "engineer@example.com")
        assert row is not None
        stored_hash = str(row[2])
        assert stored_hash != self._PASSWORD
        assert PasswordHasher().verify_password(stored_hash, self._PASSWORD) is True

    async def test_user_created_pending(self) -> None:
        """A newly signed-up user starts in the pending status."""
        # Arrange
        settings = AuthSettings(allowed_email_domains=())

        # Act
        await self._register(settings)

        # Assert
        row = await UserRepository().get_user_by_email(self._conn, "engineer@example.com")
        assert row is not None
        assert row[3] == UserStatus.PENDING.value

    async def test_verification_token_stored_hashed_not_raw(self) -> None:
        """The token in the email is raw; the DB only holds its SHA-256 hash."""
        # Arrange
        settings = AuthSettings(allowed_email_domains=())

        # Act
        await self._register(settings)

        # Assert
        message = self._mailer.last_for("engineer@example.com")
        assert message is not None
        raw_token = self._extract_token(message.body)
        stored = self._conn.execute("SELECT token_hash FROM email_verification_tokens").fetchall()
        stored_hashes = {row[0] for row in stored}
        assert raw_token not in stored_hashes
        assert TokenService().hash_token(raw_token) in stored_hashes

    @staticmethod
    def _extract_token(body: str) -> str:
        """Pull the raw token line out of the verification email body.

        The token is the only non-empty line in the template that contains no
        whitespace; every prose line does.
        """
        lines = [line.strip() for line in body.splitlines() if line.strip()]
        return next(line for line in lines if " " not in line)
