"""Orchestrates the ``POST /auth/verify`` flow.

Consumes a verification token, activates the user, and returns the safe user
projection. The presented token is hashed before lookup (constant-time equality
over high-entropy digests), matched only while unconsumed and unexpired, and
stamped consumed so it is strictly single-use. Any miss — unknown, expired, or
already-consumed — yields the same generic failure so nothing about token or
account state leaks.
"""

import duckdb

from app.auth.signup.verification_token_repository import VerificationTokenRepository
from app.auth.token_service import TokenService
from app.auth.users.user_repository import UserRepository
from app.errors.not_found_error import NotFoundError
from app.models.requests.verify_model import VerifyModel
from app.models.responses.user_response_model import UserResponseModel


class VerificationService:
    """Verify an email token and activate the corresponding user."""

    _EMAIL_INDEX: int = 1
    _STATUS_INDEX: int = 3
    _EDITION_INDEX: int = 4
    _USER_ID_INDEX: int = 1

    def __init__(
        self,
        users: UserRepository | None = None,
        token_service: TokenService | None = None,
        verification_tokens: VerificationTokenRepository | None = None,
    ) -> None:
        """Initialise the service with its collaborators.

        Args:
            users: The users-table repository.
            token_service: The token hashing service.
            verification_tokens: The verification-token repository.
        """
        self._users = users if users is not None else UserRepository()
        self._token_service = token_service if token_service is not None else TokenService()
        self._verification_tokens = (
            verification_tokens
            if verification_tokens is not None
            else VerificationTokenRepository()
        )

    async def verify(
        self, conn: duckdb.DuckDBPyConnection, model: VerifyModel
    ) -> UserResponseModel:
        """Consume the token, activate the user, and return the user model.

        Args:
            conn: The live DuckDB connection.
            model: The validated verify body carrying the raw token.

        Returns:
            The activated user as a safe :class:`UserResponseModel`.

        Raises:
            NotFoundError: When the token is unknown, expired, or already used
                (a single generic failure — no enumeration).
        """
        token_hash = self._token_service.hash_token(model.token)
        token_row = await self._verification_tokens.find_active(conn, token_hash)
        if token_row is None:
            raise NotFoundError(message="The verification token is invalid or has expired.")

        user_id = str(token_row[self._USER_ID_INDEX])
        await self._users.activate_user(conn, user_id)
        await self._verification_tokens.consume(conn, token_hash)

        user_row = await self._users.get_user_by_id(conn, user_id)
        if user_row is None:
            raise NotFoundError(message="The verification token is invalid or has expired.")

        edition = user_row[self._EDITION_INDEX]
        return UserResponseModel(
            id=user_id,
            email=str(user_row[self._EMAIL_INDEX]),
            status=str(user_row[self._STATUS_INDEX]),
            edition=str(edition) if edition is not None else None,
        )
