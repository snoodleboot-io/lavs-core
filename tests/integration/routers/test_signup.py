"""Integration tests for the ``/auth/signup`` and ``/auth/verify`` routes.

Exercises the full FastAPI stack (routing, dependency-injected managed DuckDB
connection and mailer, service execution, and the error-envelope handlers). The
client is entered as a context manager so the application lifespan runs and
populates ``app.state`` (DB connection + capture mailer); the raw verification
token is recovered straight from the in-memory mailer.
"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.mail.capture_mailer import CaptureMailer


@pytest.fixture()
def signup_client(test_db: str) -> Iterator[TestClient]:
    """Yield a lifespan-active client over the per-test temporary database."""
    from app.main import app

    with TestClient(app) as client:
        yield client


def _captured_token(client: TestClient, email: str) -> str:
    """Recover the raw verification token emailed to ``email``."""
    mailer = client.app.state.mailer
    assert isinstance(mailer, CaptureMailer)
    message = mailer.last_for(email)
    assert message is not None
    lines = [line.strip() for line in message.body.splitlines() if line.strip()]
    return next(line for line in lines if " " not in line)


class TestSignup:
    """``POST /auth/signup``."""

    def test_signup_returns_202_pending(self, signup_client: TestClient) -> None:
        """A valid sign-up is accepted with a pending-verification status."""
        # Act
        response = signup_client.post(
            "/auth/signup",
            json={"email": "engineer@example.com", "password": "correct horse battery"},
        )

        # Assert
        assert response.status_code == 202
        assert response.json() == {"status": "pending_verification"}

    def test_signup_emails_a_token(self, signup_client: TestClient) -> None:
        """Sign-up sends exactly one email carrying a usable token."""
        # Act
        signup_client.post(
            "/auth/signup",
            json={"email": "engineer@example.com", "password": "correct horse battery"},
        )

        # Assert
        token = _captured_token(signup_client, "engineer@example.com")
        assert len(token) > 0

    def test_duplicate_email_returns_409(self, signup_client: TestClient) -> None:
        """A repeated address yields a 409 conflict envelope."""
        # Arrange
        body = {"email": "dupe@example.com", "password": "correct horse battery"}
        signup_client.post("/auth/signup", json=body)

        # Act
        response = signup_client.post("/auth/signup", json=body)

        # Assert
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "conflict"

    def test_malformed_email_returns_422(self, signup_client: TestClient) -> None:
        """A malformed address is rejected before any persistence."""
        # Act
        response = signup_client.post(
            "/auth/signup",
            json={"email": "not-an-email", "password": "correct horse battery"},
        )

        # Assert
        assert response.status_code == 422


class TestVerify:
    """``POST /auth/verify``."""

    def test_verify_activates_user(self, signup_client: TestClient) -> None:
        """A captured token verifies the account and returns it active."""
        # Arrange
        signup_client.post(
            "/auth/signup",
            json={"email": "engineer@example.com", "password": "correct horse battery"},
        )
        token = _captured_token(signup_client, "engineer@example.com")

        # Act
        response = signup_client.post("/auth/verify", json={"token": token})

        # Assert
        assert response.status_code == 200
        body = response.json()
        assert body["email"] == "engineer@example.com"
        assert body["status"] == "active"
        assert "password_hash" not in body

    def test_verify_is_single_use(self, signup_client: TestClient) -> None:
        """A token cannot be redeemed twice."""
        # Arrange
        signup_client.post(
            "/auth/signup",
            json={"email": "engineer@example.com", "password": "correct horse battery"},
        )
        token = _captured_token(signup_client, "engineer@example.com")
        signup_client.post("/auth/verify", json={"token": token})

        # Act
        response = signup_client.post("/auth/verify", json={"token": token})

        # Assert
        assert response.status_code == 404

    def test_verify_unknown_token_returns_404(self, signup_client: TestClient) -> None:
        """An unknown token yields a generic not-found envelope (no enumeration)."""
        # Act
        response = signup_client.post("/auth/verify", json={"token": "never-issued"})

        # Assert
        assert response.status_code == 404


class TestSignupDomainAllowList:
    """Domain allow-list enforcement via ``LAVS_ALLOWED_EMAIL_DOMAINS``."""

    def test_disallowed_domain_returns_403(
        self, signup_client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A domain outside a configured allow-list is forbidden."""
        # Arrange
        monkeypatch.setenv("LAVS_ALLOWED_EMAIL_DOMAINS", "allowed.com")

        # Act
        response = signup_client.post(
            "/auth/signup",
            json={"email": "engineer@example.com", "password": "correct horse battery"},
        )

        # Assert
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "domain_not_allowed"

    def test_allowed_domain_passes(
        self, signup_client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A domain on the allow-list is accepted."""
        # Arrange
        monkeypatch.setenv("LAVS_ALLOWED_EMAIL_DOMAINS", "example.com")

        # Act
        response = signup_client.post(
            "/auth/signup",
            json={"email": "engineer@example.com", "password": "correct horse battery"},
        )

        # Assert
        assert response.status_code == 202
