"""Deployment configuration for the auth spine, read from the environment.

Per project convention (see :mod:`app.security.api_key_settings`), fixed
configuration is expressed through a settings class rather than bare
module-level constants, and the environment is read on demand so values can
change at runtime without re-importing. Every value may also be injected
explicitly through the constructor, which the tests use to exercise a
fully-configured (fail-closed) resolver without mutating the process
environment.
"""

import os

from app.auth.auth_mode import AuthMode


class AuthSettings:
    """Typed accessors over the ``LAVS_AUTH_*`` environment configuration."""

    _MODES_ENV_VAR: str = "LAVS_AUTH_MODES"
    _ALLOWED_DOMAINS_ENV_VAR: str = "LAVS_ALLOWED_EMAIL_DOMAINS"
    _SESSION_TTL_ENV_VAR: str = "LAVS_SESSION_TTL_SECONDS"
    _EDITION_ENV_VAR: str = "LAVS_EDITION"

    _DEFAULT_SESSION_TTL_SECONDS: int = 604800
    _DEFAULT_EDITION: str = "oss"

    def __init__(
        self,
        modes: set[AuthMode] | None = None,
        allowed_email_domains: tuple[str, ...] | None = None,
        session_ttl_seconds: int | None = None,
        edition: str | None = None,
    ) -> None:
        """Initialise the settings.

        Any argument left as ``None`` is resolved from the environment on
        access; a supplied argument overrides the environment entirely (used by
        tests to construct a fully-configured resolver).

        Args:
            modes: The enabled authentication modes.
            allowed_email_domains: The sign-up email-domain allow-list (empty
                tuple means "allow all").
            session_ttl_seconds: Session lifetime in seconds.
            edition: The deployment edition label.
        """
        self._modes = modes
        self._allowed_email_domains = allowed_email_domains
        self._session_ttl_seconds = session_ttl_seconds
        self._edition = edition

    @staticmethod
    def _split_csv(raw: str) -> list[str]:
        """Split a comma-separated env value into trimmed, non-empty items."""
        return [item.strip() for item in raw.split(",") if item.strip()]

    def modes(self) -> set[AuthMode]:
        """Return the set of enabled authentication modes.

        Unrecognised tokens are ignored so a forward-compatible config never
        crashes the foundation — a mode an out-of-core edition understands but
        this build does not is simply dropped rather than being fatal.
        """
        if self._modes is not None:
            return set(self._modes)

        raw = os.environ.get(self._MODES_ENV_VAR, "")
        recognised: set[AuthMode] = set()
        valid_values = {mode.value for mode in AuthMode}
        for token in self._split_csv(raw):
            lowered = token.lower()
            if lowered in valid_values:
                recognised.add(AuthMode(lowered))
        return recognised

    def allowed_email_domains(self) -> tuple[str, ...]:
        """Return the sign-up email-domain allow-list.

        An empty tuple means every domain is allowed. Domains are lower-cased so
        the allow-list check is case-insensitive.
        """
        if self._allowed_email_domains is not None:
            return self._allowed_email_domains

        raw = os.environ.get(self._ALLOWED_DOMAINS_ENV_VAR, "")
        return tuple(item.lower() for item in self._split_csv(raw))

    def session_ttl_seconds(self) -> int:
        """Return the session lifetime in seconds."""
        if self._session_ttl_seconds is not None:
            return self._session_ttl_seconds

        raw = os.environ.get(self._SESSION_TTL_ENV_VAR)
        if raw is None or not raw.strip():
            return self._DEFAULT_SESSION_TTL_SECONDS
        return int(raw)

    def edition(self) -> str:
        """Return the deployment edition label (defaults to ``oss``)."""
        if self._edition is not None:
            return self._edition

        raw = os.environ.get(self._EDITION_ENV_VAR)
        if raw is None or not raw.strip():
            return self._DEFAULT_EDITION
        return raw.strip()

    def password_enabled(self) -> bool:
        """Return ``True`` when the ``password`` mode is enabled."""
        return AuthMode.PASSWORD in self.modes()

    def apikey_mode_enabled(self) -> bool:
        """Return ``True`` when the ``apikey`` mode is explicitly enabled."""
        return AuthMode.APIKEY in self.modes()
