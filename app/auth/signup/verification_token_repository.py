"""Parameterized persistence for the ``email_verification_tokens`` table.

Tokens are stored **only** as their SHA-256 hash (the raw token is never
persisted), carry a DB-computed expiry, and are single-use: a consumed row is
stamped with ``consumed_at`` and never matched again. Every statement binds its
values through ``?`` placeholders — never string interpolation. Wall-clock time
is taken from the database (``CURRENT_TIMESTAMP``) rather than the process so
issuance and expiry share one clock.
"""

import duckdb


class VerificationTokenRepository:
    """Issue, look up, and consume email verification tokens."""

    async def issue(
        self,
        conn: duckdb.DuckDBPyConnection,
        token_hash: str,
        user_id: str,
        ttl_seconds: int,
    ) -> None:
        """Insert a verification-token row with a DB-computed expiry.

        Args:
            conn: The live DuckDB connection.
            token_hash: The SHA-256 hex digest of the raw token (never the raw
                token itself).
            user_id: The id of the pending user the token verifies.
            ttl_seconds: The token lifetime, added to the DB clock for expiry.
        """
        conn.execute(
            "INSERT INTO email_verification_tokens "
            "(token_hash, user_id, expires_at, consumed_at) "
            "VALUES (?, ?, CAST(CURRENT_TIMESTAMP AS TIMESTAMP) + "
            "(? * INTERVAL 1 SECOND), NULL)",
            [token_hash, user_id, ttl_seconds],
        )

    async def find_active(
        self, conn: duckdb.DuckDBPyConnection, token_hash: str
    ) -> tuple[object, ...] | None:
        """Return an unconsumed, unexpired token row, or ``None``.

        The match is by stored hash (the presented token is hashed before this
        call), so a database leak of hashes cannot yield a usable token and the
        equality is over high-entropy digests.

        Args:
            conn: The live DuckDB connection.
            token_hash: The SHA-256 hex digest of the presented token.

        Returns:
            ``(token_hash, user_id, expires_at, consumed_at)`` when a live token
            matches, otherwise ``None``.
        """
        return conn.execute(
            "SELECT token_hash, user_id, expires_at, consumed_at "
            "FROM email_verification_tokens "
            "WHERE token_hash = ? AND consumed_at IS NULL "
            "AND expires_at > CAST(CURRENT_TIMESTAMP AS TIMESTAMP)",
            [token_hash],
        ).fetchone()

    async def consume(self, conn: duckdb.DuckDBPyConnection, token_hash: str) -> None:
        """Mark a token consumed so it can never be used again.

        Args:
            conn: The live DuckDB connection.
            token_hash: The SHA-256 hex digest of the token to retire.
        """
        conn.execute(
            "UPDATE email_verification_tokens "
            "SET consumed_at = CAST(CURRENT_TIMESTAMP AS TIMESTAMP) "
            "WHERE token_hash = ?",
            [token_hash],
        )
