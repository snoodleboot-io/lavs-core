"""Integration tests for the ``/auth`` login/session/me/logout routes.

Exercises the full FastAPI stack with the ``password`` auth mode enabled so the
:class:`~app.auth.providers.password_session_provider.PasswordSessionProvider`
is registered and the resolver fails closed. Each test enters the application
lifespan (``with TestClient(app)``) so the managed DuckDB connection and the
auth spine are wired exactly as in production, and seeds users directly on that
managed connection (sign-up lives in the sibling R1 lane).
"""

import contextlib
from collections.abc import Iterator

import duckdb
import pytest
from fastapi.testclient import TestClient

from app.auth.password_hasher import PasswordHasher
from app.auth.session.session_cookie import SessionCookie
from app.auth.users.user_status import UserStatus
from app.models.types.ulid_id import new_ulid

_PASSWORD = "correct horse battery staple"


def _seed_user(conn: duckdb.DuckDBPyConnection, email: str, status: UserStatus) -> str:
    """Insert a user with a known password and return its id."""
    user_id = new_ulid()
    conn.execute(
        "INSERT INTO users (id, email, password_hash, status, edition) VALUES (?, ?, ?, ?, ?)",
        [user_id, email, PasswordHasher().hash_password(_PASSWORD), status.value, "oss"],
    )
    return user_id


@contextlib.contextmanager
def _password_client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """Yield a lifespan-entered client with the ``password`` mode enabled."""
    monkeypatch.setenv("LAVS_AUTH_MODES", "password")
    from app.main import app

    with TestClient(app) as client:
        yield client


def _login_token(response_headers: dict[str, str]) -> str:
    """Extract the raw session token from a login response's Set-Cookie."""
    set_cookie = response_headers["set-cookie"]
    return set_cookie.split(f"{SessionCookie.NAME}=")[1].split(";")[0]


class TestLogin:
    """``POST /auth/login``."""

    def test_active_user_logs_in_and_sets_secure_cookie(
        self, test_db: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A correct credential returns 200 with a hardened session cookie."""
        with _password_client(monkeypatch) as client:
            # Arrange
            from app.main import app

            _seed_user(app.state.db_connection, "active@example.com", UserStatus.ACTIVE)

            # Act
            response = client.post(
                "/auth/login", json={"email": "active@example.com", "password": _PASSWORD}
            )

            # Assert
            assert response.status_code == 200
            body = response.json()
            assert body["email"] == "active@example.com"
            assert body["status"] == UserStatus.ACTIVE.value
            assert "password_hash" not in body
            set_cookie = response.headers["set-cookie"]
            assert f"{SessionCookie.NAME}=" in set_cookie
            assert "HttpOnly" in set_cookie
            assert "Secure" in set_cookie
            assert "SameSite=lax" in set_cookie
            assert "Path=/" in set_cookie

    def test_wrong_password_returns_generic_401(
        self, test_db: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A wrong password yields a generic 401 and no cookie."""
        with _password_client(monkeypatch) as client:
            # Arrange
            from app.main import app

            _seed_user(app.state.db_connection, "active@example.com", UserStatus.ACTIVE)

            # Act
            response = client.post(
                "/auth/login", json={"email": "active@example.com", "password": "wrong"}
            )

            # Assert
            assert response.status_code == 401
            assert response.json()["error"]["message"] == "invalid credentials"
            assert "set-cookie" not in response.headers

    def test_unknown_email_returns_same_generic_401(
        self, test_db: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An unknown email is indistinguishable from a wrong password."""
        with _password_client(monkeypatch) as client:
            # Act
            response = client.post(
                "/auth/login", json={"email": "nobody@example.com", "password": _PASSWORD}
            )

            # Assert
            assert response.status_code == 401
            assert response.json()["error"]["message"] == "invalid credentials"

    def test_pending_user_returns_generic_401(
        self, test_db: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An unverified (pending) account cannot log in, without revealing why."""
        with _password_client(monkeypatch) as client:
            # Arrange
            from app.main import app

            _seed_user(app.state.db_connection, "pending@example.com", UserStatus.PENDING)

            # Act
            response = client.post(
                "/auth/login", json={"email": "pending@example.com", "password": _PASSWORD}
            )

            # Assert
            assert response.status_code == 401
            assert response.json()["error"]["message"] == "invalid credentials"

    def test_disabled_user_returns_generic_401(
        self, test_db: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A disabled account cannot log in."""
        with _password_client(monkeypatch) as client:
            # Arrange
            from app.main import app

            _seed_user(app.state.db_connection, "disabled@example.com", UserStatus.DISABLED)

            # Act
            response = client.post(
                "/auth/login", json={"email": "disabled@example.com", "password": _PASSWORD}
            )

            # Assert
            assert response.status_code == 401


class TestSessionRoundTrip:
    """Login → /me → resource → logout → /me."""

    def test_full_session_lifecycle(self, test_db: str, monkeypatch: pytest.MonkeyPatch) -> None:
        """A cookie authenticates /me and resources, and logout revokes it."""
        with _password_client(monkeypatch) as client:
            # Arrange
            from app.main import app

            _seed_user(app.state.db_connection, "active@example.com", UserStatus.ACTIVE)
            login = client.post(
                "/auth/login", json={"email": "active@example.com", "password": _PASSWORD}
            )
            token = _login_token(login.headers)
            cookies = {SessionCookie.NAME: token}

            # Act / Assert — the cookie authenticates /me...
            me = client.get("/auth/me", cookies=cookies)
            assert me.status_code == 200
            assert me.json()["email"] == "active@example.com"

            # ...and a protected resource route...
            resource = client.get("/products", cookies=cookies)
            assert resource.status_code == 200

            # ...logout revokes the session...
            logout = client.post("/auth/logout", cookies=cookies)
            assert logout.status_code == 204

            # ...after which the same cookie no longer authenticates.
            me_after = client.get("/auth/me", cookies=cookies)
            assert me_after.status_code == 401

    def test_me_without_cookie_is_401(self, test_db: str, monkeypatch: pytest.MonkeyPatch) -> None:
        """An unauthenticated /me request is rejected with 401."""
        with _password_client(monkeypatch) as client:
            # Act
            response = client.get("/auth/me")

            # Assert
            assert response.status_code == 401

    def test_logout_without_cookie_is_idempotent(
        self, test_db: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Logout succeeds even when no session cookie is present."""
        with _password_client(monkeypatch) as client:
            # Act
            response = client.post("/auth/logout")

            # Assert
            assert response.status_code == 204
