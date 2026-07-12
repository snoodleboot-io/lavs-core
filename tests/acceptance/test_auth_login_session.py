"""Acceptance: OSS login, session cookie, and logout (API_CONTRACT §2).

Drives the REAL ``/auth/login``, ``/auth/me``, and ``/auth/logout`` endpoints
against a verified user. The happy path proves login mints an ``HttpOnly``
``lavs_session`` cookie (flags asserted off the raw ``Set-Cookie`` header), that
``/auth/me`` accepts the cookie, and that logout invalidates the session so a
subsequent ``/auth/me`` is 401. Negatives pin fail-closed, non-enumerating
behaviour: logging in before verification and logging in with the wrong password
both return the *same* generic 401 (so a caller cannot distinguish "no such
user" from "bad password").

The ``/auth`` login/session endpoints are built by the R2 lane and are not in
this worktree yet, so these scenarios are expected to be RED until R2 merges.
"""

import pytest
from fastapi.testclient import TestClient

from tests.acceptance._auth_support import (
    SESSION_COOKIE_NAME,
    assert_error_envelope,
    auth_test_client,
    login,
    signup,
    signup_and_verify,
    unique_email,
)


@pytest.fixture
def auth_client(monkeypatch, test_db: str):
    """A lifespan-active client with password auth + the ``example.com`` allow-list."""
    with auth_test_client(monkeypatch) as client:
        yield client


def _session_set_cookie(response) -> str:
    """Return the ``Set-Cookie`` header line that sets the session cookie."""
    cookie_headers = response.headers.get_list("set-cookie")
    for header in cookie_headers:
        if header.startswith(f"{SESSION_COOKIE_NAME}="):
            return header
    raise AssertionError(
        f"no {SESSION_COOKIE_NAME} Set-Cookie header on login response; got {cookie_headers}"
    )


class TestLoginSession:
    """Login establishes an HttpOnly session that /auth/me honours and logout ends."""

    def test_login_sets_httponly_samesite_session_cookie(self, auth_client: TestClient) -> None:
        """A verified login returns 200 and a hardened ``lavs_session`` cookie."""
        # Arrange
        email = unique_email()
        signup_and_verify(auth_client, email)

        # Act
        response = login(auth_client, email)

        # Assert
        assert response.status_code == 200, response.text
        set_cookie = _session_set_cookie(response)
        assert "httponly" in set_cookie.lower(), set_cookie
        assert "samesite" in set_cookie.lower(), set_cookie

    def test_me_with_session_cookie_returns_the_user(self, auth_client: TestClient) -> None:
        """The session cookie from login authenticates a follow-up ``GET /auth/me``."""
        # Arrange
        email = unique_email()
        signup_and_verify(auth_client, email)
        login_response = login(auth_client, email)
        assert login_response.status_code == 200, login_response.text

        # Act — the client's cookie jar replays the session cookie automatically
        response = auth_client.get("/auth/me")

        # Assert
        assert response.status_code == 200, response.text
        assert response.json()["email"] == email

    def test_logout_invalidates_the_session(self, auth_client: TestClient) -> None:
        """After logout the previously good session no longer authenticates /auth/me."""
        # Arrange
        email = unique_email()
        signup_and_verify(auth_client, email)
        assert login(auth_client, email).status_code == 200

        # Act
        logout_response = auth_client.post("/auth/logout")
        me_response = auth_client.get("/auth/me")

        # Assert
        assert logout_response.status_code in (200, 204), logout_response.text
        assert me_response.status_code == 401, me_response.text
        assert_error_envelope(me_response.json(), "unauthorized")

    def test_login_before_verification_returns_401(self, auth_client: TestClient) -> None:
        """A pending (unverified) user cannot log in — generic 401."""
        # Arrange
        email = unique_email()
        assert signup(auth_client, email).status_code == 202

        # Act
        response = login(auth_client, email)

        # Assert
        assert response.status_code == 401, response.text
        assert_error_envelope(response.json(), "unauthorized")

    def test_wrong_password_and_unknown_email_are_indistinguishable(
        self, auth_client: TestClient
    ) -> None:
        """Wrong password and unknown email return the identical generic 401 shape."""
        # Arrange
        email = unique_email()
        signup_and_verify(auth_client, email)

        # Act
        wrong_password = login(auth_client, email, password="Totally-Wrong-1!")
        unknown_email = login(auth_client, unique_email(local="ghost"))

        # Assert — no account enumeration: same status and same envelope code
        assert wrong_password.status_code == 401, wrong_password.text
        assert unknown_email.status_code == 401, unknown_email.text
        assert_error_envelope(wrong_password.json(), "unauthorized")
        assert_error_envelope(unknown_email.json(), "unauthorized")
