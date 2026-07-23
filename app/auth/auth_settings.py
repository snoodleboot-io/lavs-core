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
    _STYTCH_PROJECT_ID_ENV_VAR: str = "LAVS_STYTCH_PROJECT_ID"
    _STYTCH_SECRET_ENV_VAR: str = "LAVS_STYTCH_SECRET"
    _STYTCH_PUBLIC_TOKEN_ENV_VAR: str = "LAVS_STYTCH_PUBLIC_TOKEN"

    _DEFAULT_SESSION_TTL_SECONDS: int = 604800
    _DEFAULT_EDITION: str = "oss"
    _EE_EDITION: str = "ee"

    def __init__(
        self,
        modes: set[AuthMode] | None = None,
        allowed_email_domains: tuple[str, ...] | None = None,
        session_ttl_seconds: int | None = None,
        edition: str | None = None,
        stytch_project_id: str | None = None,
        stytch_secret: str | None = None,
        stytch_public_token: str | None = None,
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
            stytch_project_id: The Stytch project id (EE).
            stytch_secret: The Stytch project secret (EE; never logged).
            stytch_public_token: The Stytch publishable public token (EE; safe
                to surface to browsers via ``/meta``).
        """
        self._modes = modes
        self._allowed_email_domains = allowed_email_domains
        self._session_ttl_seconds = session_ttl_seconds
        self._edition = edition
        self._stytch_project_id = stytch_project_id
        self._stytch_secret = stytch_secret
        self._stytch_public_token = stytch_public_token

    @staticmethod
    def _split_csv(raw: str) -> list[str]:
        """Split a comma-separated env value into trimmed, non-empty items."""
        return [item.strip() for item in raw.split(",") if item.strip()]

    def modes(self) -> set[AuthMode]:
        """Return the set of enabled authentication modes.

        Unrecognised tokens are ignored so a forward-compatible config never
        crashes the foundation. The ``stytch`` token is edition-gated: it is
        honoured only when :meth:`edition` is ``ee`` and stays ignored on an
        OSS deployment — exactly the pre-EE behaviour (managed identity is an
        EE capability; a stray ``stytch`` token cannot enable it on OSS).
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
        if AuthMode.STYTCH in recognised and self.edition() != self._EE_EDITION:
            recognised.discard(AuthMode.STYTCH)
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

    def stytch_enabled(self) -> bool:
        """Return ``True`` when the ``stytch`` mode is enabled (EE only)."""
        return AuthMode.STYTCH in self.modes()

    @staticmethod
    def _optional_env(name: str) -> str | None:
        """Return a trimmed env value, or ``None`` when unset or blank."""
        raw = os.environ.get(name)
        if raw is None or not raw.strip():
            return None
        return raw.strip()

    def stytch_project_id(self) -> str | None:
        """Return the Stytch project id, or ``None`` when unconfigured."""
        if self._stytch_project_id is not None:
            return self._stytch_project_id
        return self._optional_env(self._STYTCH_PROJECT_ID_ENV_VAR)

    def stytch_secret(self) -> str | None:
        """Return the Stytch project secret, or ``None`` when unconfigured.

        Read on demand and never logged — it is handed only to the Stytch SDK
        client construction.
        """
        if self._stytch_secret is not None:
            return self._stytch_secret
        return self._optional_env(self._STYTCH_SECRET_ENV_VAR)

    def stytch_public_token(self) -> str | None:
        """Return the publishable Stytch public token, or ``None`` when unset.

        This is the browser-safe publishable token surfaced through ``/meta``
        (never the secret).
        """
        if self._stytch_public_token is not None:
            return self._stytch_public_token
        return self._optional_env(self._STYTCH_PUBLIC_TOKEN_ENV_VAR)
