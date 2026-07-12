"""Deployment configuration for backend selection, read from the environment.

Per project convention (see :mod:`app.security.api_key_settings` and
:mod:`app.auth.auth_settings`), fixed configuration is expressed through a
settings class rather than bare module-level constants, and the environment is
read on demand so values can change at runtime without re-importing. Every value
may also be injected through the constructor, which tests use to exercise a
fully-configured backend without mutating the process environment.

The Postgres accessors are declared here (rather than in the R1 lane) so the
selection seam is complete: R1's ``PostgresBackend`` consumes them without
touching this class.
"""

import os

from app.backends.backend_kind import BackendKind


class BackendSettings:
    """Typed accessors over the ``LAVS_DB_*`` / ``LAVS_PG_*`` environment."""

    _BACKEND_ENV_VAR: str = "LAVS_DB_BACKEND"

    _PG_DSN_ENV_VAR: str = "LAVS_PG_DSN"
    _PG_HOST_ENV_VAR: str = "LAVS_PG_HOST"
    _PG_PORT_ENV_VAR: str = "LAVS_PG_PORT"
    _PG_DB_ENV_VAR: str = "LAVS_PG_DB"
    _PG_USER_ENV_VAR: str = "LAVS_PG_USER"
    _PG_PASSWORD_ENV_VAR: str = "LAVS_PG_PASSWORD"

    _DEFAULT_BACKEND: BackendKind = BackendKind.DUCKDB
    _DEFAULT_PG_HOST: str = "localhost"
    _DEFAULT_PG_PORT: int = 5432

    def __init__(
        self,
        backend: BackendKind | None = None,
        pg_dsn: str | None = None,
        pg_host: str | None = None,
        pg_port: int | None = None,
        pg_db: str | None = None,
        pg_user: str | None = None,
        pg_password: str | None = None,
    ) -> None:
        """Initialise the settings.

        Any argument left as ``None`` is resolved from the environment on
        access; a supplied argument overrides the environment entirely.

        Args:
            backend: The selected backend kind.
            pg_dsn: A full libpq DSN; when set it supersedes the discrete fields.
            pg_host: The Postgres host.
            pg_port: The Postgres port.
            pg_db: The Postgres database name.
            pg_user: The Postgres user.
            pg_password: The Postgres password.
        """
        self._backend = backend
        self._pg_dsn = pg_dsn
        self._pg_host = pg_host
        self._pg_port = pg_port
        self._pg_db = pg_db
        self._pg_user = pg_user
        self._pg_password = pg_password

    def backend(self) -> BackendKind:
        """Return the selected backend kind (defaults to DuckDB).

        An unrecognised ``LAVS_DB_BACKEND`` token falls back to the default so a
        typo never crashes startup silently on an unknown driver.
        """
        if self._backend is not None:
            return self._backend

        raw = os.environ.get(self._BACKEND_ENV_VAR)
        if raw is None or not raw.strip():
            return self._DEFAULT_BACKEND
        token = raw.strip().lower()
        valid = {kind.value for kind in BackendKind}
        if token not in valid:
            return self._DEFAULT_BACKEND
        return BackendKind(token)

    def pg_dsn(self) -> str | None:
        """Return the full Postgres DSN when configured, else ``None``.

        When present this is preferred over the discrete host/port/db fields.
        """
        if self._pg_dsn is not None:
            return self._pg_dsn
        raw = os.environ.get(self._PG_DSN_ENV_VAR)
        return raw if raw and raw.strip() else None

    def pg_host(self) -> str:
        """Return the Postgres host (defaults to ``localhost``)."""
        if self._pg_host is not None:
            return self._pg_host
        raw = os.environ.get(self._PG_HOST_ENV_VAR)
        return raw.strip() if raw and raw.strip() else self._DEFAULT_PG_HOST

    def pg_port(self) -> int:
        """Return the Postgres port (defaults to ``5432``)."""
        if self._pg_port is not None:
            return self._pg_port
        raw = os.environ.get(self._PG_PORT_ENV_VAR)
        if raw is None or not raw.strip():
            return self._DEFAULT_PG_PORT
        return int(raw)

    def pg_db(self) -> str | None:
        """Return the Postgres database name when configured, else ``None``."""
        if self._pg_db is not None:
            return self._pg_db
        raw = os.environ.get(self._PG_DB_ENV_VAR)
        return raw.strip() if raw and raw.strip() else None

    def pg_user(self) -> str | None:
        """Return the Postgres user when configured, else ``None``."""
        if self._pg_user is not None:
            return self._pg_user
        raw = os.environ.get(self._PG_USER_ENV_VAR)
        return raw.strip() if raw and raw.strip() else None

    def pg_password(self) -> str | None:
        """Return the Postgres password when configured, else ``None``."""
        if self._pg_password is not None:
            return self._pg_password
        raw = os.environ.get(self._PG_PASSWORD_ENV_VAR)
        return raw if raw and raw.strip() else None
