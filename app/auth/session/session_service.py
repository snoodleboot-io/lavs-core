"""Create, look up, and revoke rows in the ``sessions`` table.

A session is an opaque high-entropy token: :meth:`SessionService.create_session`
mints one, stores only its SHA-256 hash together with a TTL-derived
``expires_at``, and returns the **raw** token for the client's cookie. Lookups
present the raw token, which is re-hashed and matched against the stored hash;
an expired row never matches, so a lapsed cookie authenticates nobody. Every
statement binds its values through ``?`` placeholders.
"""

from datetime import datetime, timedelta

from app.auth.token_service import TokenService
from app.connections.db_session import DbSession
from app.models.types.ulid_id import new_ulid


class SessionService:
    """Persistence for opaque, hashed, TTL-expiring session tokens."""

    def __init__(self, token_service: TokenService | None = None) -> None:
        """Initialise the service.

        Args:
            token_service: The token minting/hashing service. Defaults to a
                fresh :class:`~app.auth.token_service.TokenService`.
        """
        self._token_service = token_service if token_service is not None else TokenService()

    def create_session(self, conn: DbSession, user_id: str, ttl_seconds: int) -> str:
        """Mint a session for a user and return its raw token.

        Args:
            conn: The live DuckDB connection.
            user_id: The id of the user the session belongs to.
            ttl_seconds: The session lifetime in seconds.

        Returns:
            The raw, high-entropy session token (store only its hash — this is
            the value handed to the client cookie and never persisted).
        """
        token = self._token_service.generate_token()
        token_hash = self._token_service.hash_token(token)
        expires_at = datetime.now() + timedelta(seconds=ttl_seconds)
        conn.execute(
            "INSERT INTO sessions (id, user_id, token_hash, expires_at) VALUES (?, ?, ?, ?)",
            [new_ulid(), user_id, token_hash, expires_at],
        )
        return token

    def lookup_active_user_id(self, conn: DbSession, token: str) -> str | None:
        """Return the user id of a live (unexpired) session, or ``None``.

        Args:
            conn: The live DuckDB connection.
            token: The raw token presented by the client.

        Returns:
            The owning user's id when a matching, unexpired session exists,
            otherwise ``None`` (unknown token or expired session).
        """
        token_hash = self._token_service.hash_token(token)
        row = conn.execute(
            "SELECT user_id FROM sessions WHERE token_hash = ? AND expires_at > ?",
            [token_hash, datetime.now()],
        ).fetchone()
        if row is None:
            return None
        return str(row[0])

    def delete_session(self, conn: DbSession, token: str) -> None:
        """Revoke a session by deleting its row (idempotent).

        Args:
            conn: The live DuckDB connection.
            token: The raw token whose session should be revoked.
        """
        token_hash = self._token_service.hash_token(token)
        conn.execute("DELETE FROM sessions WHERE token_hash = ?", [token_hash])
