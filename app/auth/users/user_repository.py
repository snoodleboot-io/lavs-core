"""Parameterized persistence for the shared ``users`` table."""

from app.auth.users.user_status import UserStatus
from app.connections.db_session import DbSession
from app.models.responses.user_response_model import UserResponseModel


class UserRepository:
    """Create, read, and activate rows in the ``users`` table.

    Every statement binds its values through ``?`` placeholders (never string
    interpolation). Read methods return the raw row (including ``password_hash``)
    so the login lane can verify a password; :meth:`create_user` returns the
    safe :class:`UserResponseModel`, which never carries the hash.
    """

    async def create_user(
        self,
        conn: DbSession,
        user_id: str,
        email: str,
        password_hash: str,
        status: UserStatus,
        edition: str | None,
    ) -> UserResponseModel:
        """Insert a new user and return its safe response model.

        Args:
            conn: The live DuckDB connection.
            user_id: The user's ULID identifier.
            email: The user's unique email address.
            password_hash: The argon2id hash of the user's password.
            status: The initial lifecycle status.
            edition: The edition the user was created under (nullable).

        Returns:
            The created user as a :class:`UserResponseModel` (no password hash).
        """
        conn.execute(
            "INSERT INTO users (id, email, password_hash, status, edition) VALUES (?, ?, ?, ?, ?)",
            [user_id, email, password_hash, status.value, edition],
        )
        return UserResponseModel(id=user_id, email=email, status=status.value, edition=edition)

    async def get_user_by_email(self, conn: DbSession, email: str) -> tuple[object, ...] | None:
        """Return the raw user row for an email, or ``None`` when absent.

        Args:
            conn: The live DuckDB connection.
            email: The email to look up.

        Returns:
            ``(id, email, password_hash, status, edition, created_at)`` or
            ``None``.
        """
        return conn.execute(
            "SELECT id, email, password_hash, status, edition, created_at "
            "FROM users WHERE email = ?",
            [email],
        ).fetchone()

    async def get_user_by_id(self, conn: DbSession, user_id: str) -> tuple[object, ...] | None:
        """Return the raw user row for an id, or ``None`` when absent.

        Args:
            conn: The live DuckDB connection.
            user_id: The user id to look up.

        Returns:
            ``(id, email, password_hash, status, edition, created_at)`` or
            ``None``.
        """
        return conn.execute(
            "SELECT id, email, password_hash, status, edition, created_at FROM users WHERE id = ?",
            [user_id],
        ).fetchone()

    async def activate_user(self, conn: DbSession, user_id: str) -> None:
        """Transition a user to the ``active`` status.

        Args:
            conn: The live DuckDB connection.
            user_id: The id of the user to activate.
        """
        conn.execute(
            "UPDATE users SET status = ? WHERE id = ?",
            [UserStatus.ACTIVE.value, user_id],
        )
