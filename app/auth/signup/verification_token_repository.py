"""Parameterized persistence for the ``email_verification_tokens`` table.

Tokens are stored **only** as their SHA-256 hash (the raw token is never
persisted), carry a Python-computed expiry, and are single-use: a consumed row is
stamped with ``consumed_at`` and never matched again. Every statement binds its
values through ``?`` placeholders — never string interpolation. Wall-clock time
is taken from the process clock (:func:`datetime.now`) and bound as a parameter,
matching :class:`~app.auth.session.session_service.SessionService` so expiry is
expressed identically — and dialect-neutrally — across DuckDB and PostgreSQL.
"""

from datetime import datetime, timedelta

from app.connections.db_session import DbSession


class VerificationTokenRepository:
    """Issue, look up, and consume email verification tokens."""

    async def issue(
        self,
        conn: DbSession,
        token_hash: str,
        user_id: str,
        ttl_seconds: int,
    ) -> None:
        """Insert a verification-token row with a Python-computed expiry.

        The expiry is computed in Python (``datetime.now() + ttl``) and bound as
        a parameter rather than derived with an in-SQL interval expression, so the
        statement parses identically on DuckDB and PostgreSQL.

        Args:
            conn: The live database session.
            token_hash: The SHA-256 hex digest of the raw token (never the raw
                token itself).
            user_id: The id of the pending user the token verifies.
            ttl_seconds: The token lifetime, added to the clock for expiry.
        """
        expires_at = datetime.now() + timedelta(seconds=ttl_seconds)
        conn.execute(
            "INSERT INTO email_verification_tokens "
            "(token_hash, user_id, expires_at, consumed_at) "
            "VALUES (?, ?, ?, NULL)",
            [token_hash, user_id, expires_at],
        )

    async def find_active(self, conn: DbSession, token_hash: str) -> tuple[object, ...] | None:
        """Return an unconsumed, unexpired token row, or ``None``.

        The match is by stored hash (the presented token is hashed before this
        call), so a database leak of hashes cannot yield a usable token and the
        equality is over high-entropy digests. Expiry is checked against a bound
        current timestamp so the comparison is dialect-neutral.

        Args:
            conn: The live database session.
            token_hash: The SHA-256 hex digest of the presented token.

        Returns:
            ``(token_hash, user_id, expires_at, consumed_at)`` when a live token
            matches, otherwise ``None``.
        """
        return conn.execute(
            "SELECT token_hash, user_id, expires_at, consumed_at "
            "FROM email_verification_tokens "
            "WHERE token_hash = ? AND consumed_at IS NULL "
            "AND expires_at > ?",
            [token_hash, datetime.now()],
        ).fetchone()

    async def consume(self, conn: DbSession, token_hash: str) -> None:
        """Mark a token consumed so it can never be used again.

        Args:
            conn: The live database session.
            token_hash: The SHA-256 hex digest of the token to retire.
        """
        conn.execute(
            "UPDATE email_verification_tokens SET consumed_at = ? WHERE token_hash = ?",
            [datetime.now(), token_hash],
        )
