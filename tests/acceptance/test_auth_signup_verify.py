"""Acceptance: OSS sign-up + email/domain verification (API_CONTRACT §2).

Drives the REAL ``/auth/signup`` and ``/auth/verify`` endpoints end to end with
the auth providers configured (default-OPEN otherwise). Happy path: an
allow-listed domain signs up to a ``pending_verification`` state, the
verification token is recovered from the captured email, and posting it
activates the user. Negatives pin the contract's failure codes: a disallowed
domain is ``403 domain_not_allowed`` and a duplicate email is ``409 conflict``,
each as the uniform error envelope.

These endpoints are built by the R1 lane and are not in this worktree yet, so
every scenario here is expected to be RED (route missing) until R1 merges.
"""

import pytest
from fastapi.testclient import TestClient

from app.auth.users.user_status import UserStatus
from tests.acceptance._auth_support import (
    assert_error_envelope,
    auth_test_client,
    signup,
    unique_email,
    verification_token_for,
)


@pytest.fixture
def auth_client(monkeypatch, test_db: str):
    """A lifespan-active client with password auth + the ``example.com`` allow-list."""
    with auth_test_client(monkeypatch) as client:
        yield client


class TestSignupVerify:
    """Sign-up establishes a pending user; verification activates it."""

    def test_signup_allowed_domain_returns_202_pending(self, auth_client: TestClient) -> None:
        """An allow-listed sign-up is accepted 202 in a pending-verification state."""
        # Arrange
        email = unique_email()

        # Act
        response = signup(auth_client, email)

        # Assert
        assert response.status_code == 202, response.text
        assert response.json()["status"] == "pending_verification"

    def test_verify_activates_the_pending_user(self, auth_client: TestClient) -> None:
        """Posting the emailed token flips the user to active and returns 200 {user}."""
        # Arrange
        email = unique_email()
        signup_response = signup(auth_client, email)
        assert signup_response.status_code == 202, signup_response.text
        token = verification_token_for(auth_client, email)

        # Act
        response = auth_client.post("/auth/verify", json={"token": token})

        # Assert
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["email"] == email
        assert body["status"] == UserStatus.ACTIVE.value

    def test_signup_disallowed_domain_returns_403_domain_not_allowed(
        self, auth_client: TestClient
    ) -> None:
        """A sign-up outside the allow-list is refused 403 with a domain envelope."""
        # Arrange
        email = unique_email(domain="not-allowed.org")

        # Act
        response = signup(auth_client, email)

        # Assert
        assert response.status_code == 403, response.text
        assert_error_envelope(response.json(), "domain_not_allowed")

    def test_duplicate_email_returns_409_conflict(self, auth_client: TestClient) -> None:
        """Registering an email that already exists is a 409 conflict envelope."""
        # Arrange
        email = unique_email()
        first = signup(auth_client, email)
        assert first.status_code == 202, first.text

        # Act
        duplicate = signup(auth_client, email)

        # Assert
        assert duplicate.status_code == 409, duplicate.text
        assert_error_envelope(duplicate.json(), "conflict")
