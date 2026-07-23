"""Configuration for the ``/auth/*`` per-IP rate limiter, read on demand.

Per project convention (see :mod:`app.security.api_key_settings` and
:mod:`app.auth.auth_settings`), fixed configuration is expressed through a
settings class rather than bare module-level constants, and the environment is
read on demand so values can change at runtime without re-importing. Every
value may also be injected explicitly through the constructor, which the tests
use to exercise a fully-configured limiter without mutating the process
environment.

Default posture: **disabled** (``LAVS_AUTH_RATE_LIMIT`` defaults to ``0``).
This keeps every bare ``TestClient`` — and the whole existing test suite —
byte-for-byte unaffected: the middleware is always wired but performs no
counting until an operator opts in by setting a positive limit (typically via
the Helm chart's environment). ``0`` (or an unset variable) disables limiting.
"""

import os


class RateLimitSettings:
    """Typed accessors over the ``LAVS_AUTH_RATE_*`` environment configuration."""

    _LIMIT_ENV_VAR: str = "LAVS_AUTH_RATE_LIMIT"
    _WINDOW_ENV_VAR: str = "LAVS_AUTH_RATE_WINDOW_SECONDS"
    _TRUST_FORWARDED_ENV_VAR: str = "LAVS_AUTH_RATE_TRUST_FORWARDED_FOR"

    _DEFAULT_LIMIT: int = 0
    _DEFAULT_WINDOW_SECONDS: int = 60
    _DEFAULT_MAX_TRACKED_CLIENTS: int = 1024
    _TRUTHY_VALUES: tuple[str, ...] = ("1", "true", "yes", "on")

    def __init__(
        self,
        limit: int | None = None,
        window_seconds: int | None = None,
        trust_forwarded_for: bool | None = None,
        max_tracked_clients: int | None = None,
    ) -> None:
        """Initialise the settings.

        Any argument left as ``None`` is resolved from the environment on
        access; a supplied argument overrides the environment entirely (used by
        tests to construct an enabled limiter deterministically).

        Args:
            limit: Maximum requests allowed per client per window; ``0``
                disables limiting.
            window_seconds: The sliding-window length in seconds.
            trust_forwarded_for: Whether to honour ``X-Forwarded-For`` when
                extracting the client IP.
            max_tracked_clients: Upper bound on distinct client buckets kept in
                memory (fixed configuration; not environment-driven).
        """
        self._limit = limit
        self._window_seconds = window_seconds
        self._trust_forwarded_for = trust_forwarded_for
        self._max_tracked_clients = (
            max_tracked_clients
            if max_tracked_clients is not None
            else self._DEFAULT_MAX_TRACKED_CLIENTS
        )

    @staticmethod
    def _int_or_default(raw: str, default: int) -> int:
        """Parse an env value as an int, falling back to ``default`` when malformed.

        The settings are read per request inside the middleware, so a malformed
        value must never raise — that would turn an operator typo into a 500 on
        every ``/auth/*`` request. Falling back keeps the deployment on the safe
        documented default instead.
        """
        try:
            return int(raw)
        except ValueError:
            return default

    def limit(self) -> int:
        """Return the per-client request budget per window (``0`` disables)."""
        if self._limit is not None:
            return self._limit

        raw = os.environ.get(self._LIMIT_ENV_VAR)
        if raw is None or not raw.strip():
            return self._DEFAULT_LIMIT
        return self._int_or_default(raw, self._DEFAULT_LIMIT)

    def window_seconds(self) -> int:
        """Return the sliding-window length in seconds."""
        if self._window_seconds is not None:
            return self._window_seconds

        raw = os.environ.get(self._WINDOW_ENV_VAR)
        if raw is None or not raw.strip():
            return self._DEFAULT_WINDOW_SECONDS
        return self._int_or_default(raw, self._DEFAULT_WINDOW_SECONDS)

    def trust_forwarded_for(self) -> bool:
        """Return whether ``X-Forwarded-For`` may name the client IP.

        Defaults to **off**: the header is trivially spoofable by any direct
        caller, so honouring it unconditionally would let an attacker rotate
        forged addresses to evade the per-IP budget. Enable only when a
        trusted reverse proxy in front of the app is known to overwrite the
        header with the real client address.
        """
        if self._trust_forwarded_for is not None:
            return self._trust_forwarded_for

        raw = os.environ.get(self._TRUST_FORWARDED_ENV_VAR, "")
        return raw.strip().lower() in self._TRUTHY_VALUES

    def max_tracked_clients(self) -> int:
        """Return the cap on distinct client buckets held in memory."""
        return self._max_tracked_clients

    def enabled(self) -> bool:
        """Return ``True`` when limiting is active (positive limit and window)."""
        return self.limit() > 0 and self.window_seconds() > 0
