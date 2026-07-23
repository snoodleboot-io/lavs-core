"""Parameterized persistence for the ``email_verification_tokens`` table.

Tokens are stored **only** as their SHA-256 hash (the raw token is never
persisted), carry a Python-computed expiry, and are single-use: a consumed row is
stamped with ``consumed_at`` and never matched again. Every statement binds its
values through ``?`` placeholders — never string interpolation. Wall-clock time
is always taken in UTC (:func:`_utc_now`) and bound as a timezone-naive value,
matching :class:`~app.auth.session.session_service.SessionService`: the
``email_verification_tokens`` columns are naive ``TIMESTAMP`` on both DuckDB and
PostgreSQL, so a naive-UTC bind round-trips verbatim on both backends, whereas a
tz-aware bind would be cast through the session time zone.
"""

from datetime import UTC, datetime, timedelta

from app.connections.db_session import DbSession


def _utc_now() -> datetime:
    """Return the current UTC wall-clock time as a naive ``datetime``.

    Computed as :func:`datetime.now` in UTC with ``tzinfo`` stripped so the
    value binds into the naive ``TIMESTAMP`` columns identically on DuckDB and
    PostgreSQL, independent of the host or database session time zone.

    Returns:
        The current instant in UTC, timezone-naive.
    """
    return datetime.now(UTC).replace(tzinfo=None)


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

        The expiry is computed in Python (UTC now + ttl, bound naive) rather
        than derived with an in-SQL interval expression, so the statement parses
        identically on DuckDB and PostgreSQL and never depends on either
        backend's session time zone.

        Args:
            conn: The live database session.
            token_hash: The SHA-256 hex digest of the raw token (never the raw
                token itself).
            user_id: The id of the pending user the token verifies.
            ttl_seconds: The token lifetime, added to the clock for expiry.
        """
        expires_at = _utc_now() + timedelta(seconds=ttl_seconds)
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
            [token_hash, _utc_now()],
        ).fetchone()

    async def consume(self, conn: DbSession, token_hash: str) -> None:
        """Mark a token consumed so it can never be used again.

        Args:
            conn: The live database session.
            token_hash: The SHA-256 hex digest of the token to retire.
        """
        conn.execute(
            "UPDATE email_verification_tokens SET consumed_at = ? WHERE token_hash = ?",
            [_utc_now(), token_hash],
        )
