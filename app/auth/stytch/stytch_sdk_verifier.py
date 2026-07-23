"""The production :class:`StytchVerifier` backed by the official Stytch SDK."""

import logging

from stytch import Client
from stytch.consumer.models.users import User
from stytch.core.response_base import StytchError

from app.auth.auth_settings import AuthSettings
from app.auth.stytch.stytch_verification import StytchVerification
from app.auth.stytch.stytch_verifier import StytchVerifier

logger = logging.getLogger("lavs-api")


class StytchSdkVerifier(StytchVerifier):
    """Verify Stytch session credentials through ``stytch.Client``.

    The client is constructed lazily, on the first verification, from the
    ``LAVS_STYTCH_PROJECT_ID`` / ``LAVS_STYTCH_SECRET`` accessors on
    :class:`AuthSettings` — the secret is read on demand and never logged.
    A token containing exactly two dots is treated as a session JWT, anything
    else as an opaque session token (the two credential shapes Stytch issues).
    Any verification failure — :class:`StytchError`, missing configuration, or
    an unexpected transport error — resolves to ``None`` so the caller's single
    generic 401 posture holds; the presented token itself is never logged.
    """

    def __init__(self, settings: AuthSettings | None = None, client: Client | None = None) -> None:
        """Initialise the verifier.

        Args:
            settings: The deployment auth settings the client is built from.
                Defaults to an environment-backed :class:`AuthSettings`.
            client: An already-constructed Stytch client. When supplied it is
                used as-is and no settings are read (test/DI seam).
        """
        self._settings = settings if settings is not None else AuthSettings()
        self._client = client

    def _resolve_client(self) -> Client | None:
        """Return the Stytch client, building it from settings on first use."""
        if self._client is not None:
            return self._client

        project_id = self._settings.stytch_project_id()
        secret = self._settings.stytch_secret()
        if not project_id or not secret:
            logger.warning("Stytch verification requested but the project id/secret is not set.")
            return None

        self._client = Client(project_id=project_id, secret=secret)
        return self._client

    @staticmethod
    def _primary_email(user: User) -> str | None:
        """Return the user's first **verified** email, or ``None``.

        Unverified addresses are never surfaced: the callback maps this email
        onto the shared ``users`` table, so trusting an unverified address
        would let an attacker claim a victim's account by merely *entering*
        their email at Stytch. With no verified email the identity resolves
        with ``email=None`` and the callers' generic-401 paths fail closed.
        """
        for email in user.emails:
            if email.verified:
                return email.email
        return None

    async def verify(self, token: str) -> StytchVerification | None:
        """Verify a Stytch session token or session JWT via the SDK.

        Args:
            token: The raw Stytch session token or session JWT.

        Returns:
            The verified identity, or ``None`` on any failure (invalid or
            expired token, missing configuration, or a transport error).
        """
        client = self._resolve_client()
        if client is None:
            return None

        try:
            if token.count(".") == 2:
                response = await client.sessions.authenticate_async(session_jwt=token)
            else:
                response = await client.sessions.authenticate_async(session_token=token)
        except StytchError as error:
            # Log only the exception class and Stytch's own status/error_type —
            # never the presented token and never the full error payload.
            logger.warning(
                "Stytch session verification failed: %s (status=%s, error_type=%s).",
                type(error).__name__,
                error.details.status_code,
                error.details.error_type,
            )
            return None
        except Exception:
            logger.exception("Stytch session verification failed unexpectedly.")
            return None

        return StytchVerification(
            user_id=response.user.user_id,
            email=self._primary_email(response.user),
        )
