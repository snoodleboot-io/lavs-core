"""Orchestrates the ``POST /auth/signup`` flow.

Security posture:
- The password is only ever stored as an argon2id hash (never plaintext).
- The verification token is high-entropy, stored **hashed**, expiring, and
  single-use; only the raw token leaves the process, via the mailer.
- Beyond the contract-mandated 409 on an existing address, the response reveals
  nothing about account existence (no enumeration).
"""

import duckdb

from app.auth.auth_settings import AuthSettings
from app.auth.password_hasher import PasswordHasher
from app.auth.signup.verification_email import VerificationEmail
from app.auth.signup.verification_settings import VerificationSettings
from app.auth.signup.verification_token_repository import VerificationTokenRepository
from app.auth.token_service import TokenService
from app.auth.users.user_repository import UserRepository
from app.auth.users.user_status import UserStatus
from app.errors.conflict_error import ConflictError
from app.errors.domain_not_allowed_error import DomainNotAllowedError
from app.mail.mailer import Mailer
from app.models.requests.signup_model import SignupModel
from app.models.types.ulid_id import new_ulid


class SignupService:
    """Register a pending user and issue an email verification token."""

    def __init__(
        self,
        users: UserRepository | None = None,
        password_hasher: PasswordHasher | None = None,
        token_service: TokenService | None = None,
        verification_tokens: VerificationTokenRepository | None = None,
        verification_email: VerificationEmail | None = None,
        verification_settings: VerificationSettings | None = None,
    ) -> None:
        """Initialise the service with its collaborators.

        Every collaborator defaults to a fresh, stateless instance; tests may
        inject fakes or pinned settings.

        Args:
            users: The users-table repository.
            password_hasher: The argon2id password hasher.
            token_service: The high-entropy token mint/hash service.
            verification_tokens: The verification-token repository.
            verification_email: The verification email renderer.
            verification_settings: The verification-token lifetime settings.
        """
        self._users = users if users is not None else UserRepository()
        self._password_hasher = password_hasher if password_hasher is not None else PasswordHasher()
        self._token_service = token_service if token_service is not None else TokenService()
        self._verification_tokens = (
            verification_tokens
            if verification_tokens is not None
            else VerificationTokenRepository()
        )
        self._verification_email = (
            verification_email if verification_email is not None else VerificationEmail()
        )
        self._verification_settings = (
            verification_settings if verification_settings is not None else VerificationSettings()
        )

    async def register(
        self,
        conn: duckdb.DuckDBPyConnection,
        mailer: Mailer,
        model: SignupModel,
        settings: AuthSettings,
    ) -> None:
        """Register a pending user and email them a verification token.

        Args:
            conn: The live DuckDB connection.
            mailer: The transport used to deliver the raw token.
            model: The validated (already normalised) sign-up body.
            settings: The auth settings supplying the domain allow-list and
                deployment edition.

        Raises:
            DomainNotAllowedError: When the email's domain is not allow-listed.
            ConflictError: When a user with that email already exists.
        """
        email = model.email
        self._assert_domain_allowed(email, settings)
        await self._assert_email_available(conn, email)

        password_hash = self._password_hasher.hash_password(model.password)
        user_id = new_ulid()
        await self._users.create_user(
            conn,
            user_id=user_id,
            email=email,
            password_hash=password_hash,
            status=UserStatus.PENDING,
            edition=settings.edition(),
        )

        raw_token = self._token_service.generate_token()
        await self._verification_tokens.issue(
            conn,
            token_hash=self._token_service.hash_token(raw_token),
            user_id=user_id,
            ttl_seconds=self._verification_settings.ttl_seconds(),
        )

        mailer.send(
            to=email,
            subject=self._verification_email.subject(),
            body=self._verification_email.body(raw_token),
        )

    def _assert_domain_allowed(self, email: str, settings: AuthSettings) -> None:
        """Raise when a non-empty allow-list excludes the email's domain.

        Args:
            email: The normalised (lower-cased) email address.
            settings: The auth settings carrying the allow-list.

        Raises:
            DomainNotAllowedError: When the domain is not permitted.
        """
        allowed = settings.allowed_email_domains()
        if not allowed:
            return
        domain = email.rsplit("@", 1)[-1]
        if domain not in allowed:
            raise DomainNotAllowedError(
                message="This email domain is not permitted for sign-up.",
                details={"domain": domain},
            )

    async def _assert_email_available(self, conn: duckdb.DuckDBPyConnection, email: str) -> None:
        """Raise a generic conflict when the email is already registered.

        Args:
            conn: The live DuckDB connection.
            email: The normalised email address.

        Raises:
            ConflictError: When a user with that email already exists.
        """
        existing = await self._users.get_user_by_email(conn, email)
        if existing is not None:
            raise ConflictError(message="This email address cannot be registered.")
