"""Deployment configuration for the email-verification token lifetime.

Mirrors :class:`~app.auth.auth_settings.AuthSettings`: fixed configuration is
expressed through a settings class read from the environment on demand, and
every value may be injected through the constructor so tests can pin a lifetime
without mutating the process environment.
"""

import os


class VerificationSettings:
    """Typed accessor over the email-verification token lifetime configuration."""

    _TTL_ENV_VAR: str = "LAVS_EMAIL_VERIFICATION_TTL_SECONDS"
    _DEFAULT_TTL_SECONDS: int = 86400

    def __init__(self, ttl_seconds: int | None = None) -> None:
        """Initialise the settings.

        Args:
            ttl_seconds: The verification-token lifetime in seconds. When left
                as ``None`` it is resolved from the environment on access,
                defaulting to one day.
        """
        self._ttl_seconds = ttl_seconds

    def ttl_seconds(self) -> int:
        """Return the verification-token lifetime in seconds."""
        if self._ttl_seconds is not None:
            return self._ttl_seconds

        raw = os.environ.get(self._TTL_ENV_VAR)
        if raw is None or not raw.strip():
            return self._DEFAULT_TTL_SECONDS
        return int(raw)
