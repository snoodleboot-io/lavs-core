"""Unit tests for :class:`StytchSdkVerifier` over a fake SDK client (no network)."""

import asyncio
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase

import pytest
from stytch.core.response_base import StytchError, StytchErrorDetails

from app.auth.auth_settings import AuthSettings
from app.auth.stytch.stytch_sdk_verifier import StytchSdkVerifier


def _stytch_error() -> StytchError:
    """Build a realistic SDK error (what an invalid/expired session raises)."""
    return StytchError(
        StytchErrorDetails(
            status_code=401,
            request_id="request-id-test",
            error_type="session_not_found",
            error_message="Session expired or not found.",
            error_url="https://stytch.com/docs/api/errors/401",
        )
    )


class FakeSessions:
    """Stand-in for ``client.sessions`` recording the authenticate call."""

    def __init__(self, response: object = None, error: Exception | None = None) -> None:
        """Initialise the fake.

        Args:
            response: The response to return on success.
            error: When set, the exception raised instead of responding.
        """
        self._response = response
        self._error = error
        self.calls: list[dict[str, str | None]] = []

    async def authenticate_async(
        self, session_token: str | None = None, session_jwt: str | None = None
    ) -> object:
        """Record the call and answer with the configured response or error."""
        self.calls.append({"session_token": session_token, "session_jwt": session_jwt})
        if self._error is not None:
            raise self._error
        return self._response


def _fake_client(sessions: FakeSessions) -> object:
    """Wrap a fake sessions API in a client-shaped object."""
    return SimpleNamespace(sessions=sessions)


def _sdk_response(user_id: str, emails: list[tuple[str, bool]]) -> object:
    """Build a response shaped like the SDK's ``AuthenticateResponse``.

    Args:
        user_id: The Stytch user id.
        emails: ``(address, verified)`` pairs in SDK order.

    Returns:
        An object with the ``.user.user_id`` / ``.user.emails`` surface.
    """
    email_objects = [
        SimpleNamespace(email=address, verified=verified) for address, verified in emails
    ]
    return SimpleNamespace(user=SimpleNamespace(user_id=user_id, emails=email_objects))


def _verifier(sessions: FakeSessions) -> StytchSdkVerifier:
    """Build a verifier over a fake client (settings never consulted)."""
    return StytchSdkVerifier(settings=AuthSettings(), client=_fake_client(sessions))  # type: ignore[arg-type]


class TestStytchSdkVerifier(IsolatedAsyncioTestCase):
    """Token routing, identity mapping, and fail-closed error handling."""

    async def test_opaque_token_verifies_as_session_token(self) -> None:
        """A dot-less token is authenticated as ``session_token``."""
        # Arrange
        sessions = FakeSessions(
            response=_sdk_response("user-test-1", [("engineer@example.com", True)])
        )

        # Act
        verification = await _verifier(sessions).verify("opaque-session-token")

        # Assert
        assert verification is not None
        assert verification.user_id == "user-test-1"
        assert verification.email == "engineer@example.com"
        assert sessions.calls == [{"session_token": "opaque-session-token", "session_jwt": None}]

    async def test_jwt_shaped_token_verifies_as_session_jwt(self) -> None:
        """A three-segment token (two dots) is authenticated as ``session_jwt``."""
        # Arrange
        sessions = FakeSessions(
            response=_sdk_response("user-test-2", [("engineer@example.com", True)])
        )
        jwt = "eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJ1c2VyIn0.signature"

        # Act
        verification = await _verifier(sessions).verify(jwt)

        # Assert
        assert verification is not None
        assert sessions.calls == [{"session_token": None, "session_jwt": jwt}]

    async def test_verified_email_wins_over_surrounding_unverified_ones(self) -> None:
        """The verified email is surfaced even when unverified ones precede it."""
        # Arrange
        sessions = FakeSessions(
            response=_sdk_response(
                "user-test-3",
                [
                    ("unverified@example.com", False),
                    ("verified@example.com", True),
                    ("another-unverified@example.com", False),
                ],
            )
        )

        # Act
        verification = await _verifier(sessions).verify("token")

        # Assert
        assert verification is not None
        assert verification.email == "verified@example.com"

    async def test_unverified_only_emails_yield_none_email(self) -> None:
        """With no verified email the identity fails closed to ``email=None``.

        An unverified address must never be surfaced: the callback maps the
        email onto the users table, so trusting it would allow account
        takeover by merely entering a victim's email at Stytch.
        """
        # Arrange
        sessions = FakeSessions(
            response=_sdk_response("user-test-4", [("only@example.com", False)])
        )

        # Act
        verification = await _verifier(sessions).verify("token")

        # Assert
        assert verification is not None
        assert verification.email is None

    async def test_no_emails_yields_none_email(self) -> None:
        """An identity without any email verifies with ``email=None``."""
        # Arrange
        sessions = FakeSessions(response=_sdk_response("user-test-5", []))

        # Act
        verification = await _verifier(sessions).verify("token")

        # Assert
        assert verification is not None
        assert verification.email is None

    async def test_stytch_error_returns_none(self) -> None:
        """The SDK's invalid-session error resolves to None, never a raise."""
        # Arrange
        sessions = FakeSessions(error=_stytch_error())

        # Act / Assert
        assert await _verifier(sessions).verify("expired-token") is None

    async def test_unexpected_error_returns_none(self) -> None:
        """A transport-level failure also fails closed to None."""
        # Arrange
        sessions = FakeSessions(error=RuntimeError("connection reset"))

        # Act / Assert
        assert await _verifier(sessions).verify("any-token") is None

    async def test_missing_configuration_returns_none(self) -> None:
        """With no client and no project id/secret, verification declines."""
        # Arrange — settings with explicitly-absent Stytch configuration
        verifier = StytchSdkVerifier(settings=AuthSettings(stytch_project_id="", stytch_secret=""))

        # Act / Assert
        assert await verifier.verify("any-token") is None


class TestConfigurationResolution:
    """Configuration is read lazily and only when no client was injected."""

    def test_injected_client_bypasses_settings(self) -> None:
        """A supplied client is used as-is (no env/settings reads needed)."""
        # Arrange — settings whose Stytch config is explicitly absent: were the
        # injected client not used, verification could only fail closed.
        sessions = FakeSessions(
            response=_sdk_response("user-test-di", [("engineer@example.com", True)])
        )
        verifier = StytchSdkVerifier(
            settings=AuthSettings(stytch_project_id="", stytch_secret=""),
            client=_fake_client(sessions),  # type: ignore[arg-type]
        )

        # Act
        verification = asyncio.run(verifier.verify("opaque-token"))

        # Assert — the injected client answered despite the empty settings
        assert verification is not None
        assert verification.user_id == "user-test-di"

    def test_unconfigured_environment_fails_closed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Without project id and secret in the env, verification declines."""
        # Arrange
        monkeypatch.delenv("LAVS_STYTCH_PROJECT_ID", raising=False)
        monkeypatch.delenv("LAVS_STYTCH_SECRET", raising=False)
        verifier = StytchSdkVerifier(settings=AuthSettings())

        # Act / Assert
        assert asyncio.run(verifier.verify("any-token")) is None
