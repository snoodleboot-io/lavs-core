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
    """Typed accessors over the ``LAVS_DB_*`` / ``LAVS_PG_*`` / ``LAVS_MYSQL_*`` / ``LAVS_MSSQL_*`` environment."""

    _BACKEND_ENV_VAR: str = "LAVS_DB_BACKEND"

    _PG_DSN_ENV_VAR: str = "LAVS_PG_DSN"
    _PG_HOST_ENV_VAR: str = "LAVS_PG_HOST"
    _PG_PORT_ENV_VAR: str = "LAVS_PG_PORT"
    _PG_DB_ENV_VAR: str = "LAVS_PG_DB"
    _PG_USER_ENV_VAR: str = "LAVS_PG_USER"
    _PG_PASSWORD_ENV_VAR: str = "LAVS_PG_PASSWORD"

    _MYSQL_DSN_ENV_VAR: str = "LAVS_MYSQL_DSN"
    _MYSQL_HOST_ENV_VAR: str = "LAVS_MYSQL_HOST"
    _MYSQL_PORT_ENV_VAR: str = "LAVS_MYSQL_PORT"
    _MYSQL_DB_ENV_VAR: str = "LAVS_MYSQL_DB"
    _MYSQL_USER_ENV_VAR: str = "LAVS_MYSQL_USER"
    _MYSQL_PASSWORD_ENV_VAR: str = "LAVS_MYSQL_PASSWORD"

    _MSSQL_DSN_ENV_VAR: str = "LAVS_MSSQL_DSN"
    _MSSQL_HOST_ENV_VAR: str = "LAVS_MSSQL_HOST"
    _MSSQL_PORT_ENV_VAR: str = "LAVS_MSSQL_PORT"
    _MSSQL_DB_ENV_VAR: str = "LAVS_MSSQL_DB"
    _MSSQL_USER_ENV_VAR: str = "LAVS_MSSQL_USER"
    _MSSQL_PASSWORD_ENV_VAR: str = "LAVS_MSSQL_PASSWORD"

    _DEFAULT_BACKEND: BackendKind = BackendKind.DUCKDB
    _DEFAULT_PG_HOST: str = "localhost"
    _DEFAULT_PG_PORT: int = 5432
    _DEFAULT_MYSQL_HOST: str = "localhost"
    _DEFAULT_MYSQL_PORT: int = 3306
    _DEFAULT_MSSQL_HOST: str = "localhost"
    _DEFAULT_MSSQL_PORT: int = 1433

    def __init__(
        self,
        backend: BackendKind | None = None,
        pg_dsn: str | None = None,
        pg_host: str | None = None,
        pg_port: int | None = None,
        pg_db: str | None = None,
        pg_user: str | None = None,
        pg_password: str | None = None,
        mysql_dsn: str | None = None,
        mysql_host: str | None = None,
        mysql_port: int | None = None,
        mysql_db: str | None = None,
        mysql_user: str | None = None,
        mysql_password: str | None = None,
        mssql_dsn: str | None = None,
        mssql_host: str | None = None,
        mssql_port: int | None = None,
        mssql_db: str | None = None,
        mssql_user: str | None = None,
        mssql_password: str | None = None,
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
            mysql_dsn: A full MySQL DSN; when set it supersedes the discrete fields.
            mysql_host: The MySQL host.
            mysql_port: The MySQL port.
            mysql_db: The MySQL database name.
            mysql_user: The MySQL user.
            mysql_password: The MySQL password.
            mssql_dsn: A full SQL Server DSN; when set it supersedes the discrete fields.
            mssql_host: The SQL Server host.
            mssql_port: The SQL Server port.
            mssql_db: The SQL Server database name.
            mssql_user: The SQL Server user.
            mssql_password: The SQL Server password.
        """
        self._backend = backend
        self._pg_dsn = pg_dsn
        self._pg_host = pg_host
        self._pg_port = pg_port
        self._pg_db = pg_db
        self._pg_user = pg_user
        self._pg_password = pg_password
        self._mysql_dsn = mysql_dsn
        self._mysql_host = mysql_host
        self._mysql_port = mysql_port
        self._mysql_db = mysql_db
        self._mysql_user = mysql_user
        self._mysql_password = mysql_password
        self._mssql_dsn = mssql_dsn
        self._mssql_host = mssql_host
        self._mssql_port = mssql_port
        self._mssql_db = mssql_db
        self._mssql_user = mssql_user
        self._mssql_password = mssql_password

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

    def mysql_dsn(self) -> str | None:
        """Return the full MySQL DSN when configured, else ``None``.

        When present this is preferred over the discrete host/port/db fields.
        """
        if self._mysql_dsn is not None:
            return self._mysql_dsn
        raw = os.environ.get(self._MYSQL_DSN_ENV_VAR)
        return raw if raw and raw.strip() else None

    def mysql_host(self) -> str:
        """Return the MySQL host (defaults to ``localhost``)."""
        if self._mysql_host is not None:
            return self._mysql_host
        raw = os.environ.get(self._MYSQL_HOST_ENV_VAR)
        return raw.strip() if raw and raw.strip() else self._DEFAULT_MYSQL_HOST

    def mysql_port(self) -> int:
        """Return the MySQL port (defaults to ``3306``)."""
        if self._mysql_port is not None:
            return self._mysql_port
        raw = os.environ.get(self._MYSQL_PORT_ENV_VAR)
        if raw is None or not raw.strip():
            return self._DEFAULT_MYSQL_PORT
        return int(raw)

    def mysql_db(self) -> str | None:
        """Return the MySQL database name when configured, else ``None``."""
        if self._mysql_db is not None:
            return self._mysql_db
        raw = os.environ.get(self._MYSQL_DB_ENV_VAR)
        return raw.strip() if raw and raw.strip() else None

    def mysql_user(self) -> str | None:
        """Return the MySQL user when configured, else ``None``."""
        if self._mysql_user is not None:
            return self._mysql_user
        raw = os.environ.get(self._MYSQL_USER_ENV_VAR)
        return raw.strip() if raw and raw.strip() else None

    def mysql_password(self) -> str | None:
        """Return the MySQL password when configured, else ``None``."""
        if self._mysql_password is not None:
            return self._mysql_password
        raw = os.environ.get(self._MYSQL_PASSWORD_ENV_VAR)
        return raw if raw and raw.strip() else None

    def mssql_dsn(self) -> str | None:
        """Return the full SQL Server DSN when configured, else ``None``.

        When present this is preferred over the discrete host/port/db fields.
        """
        if self._mssql_dsn is not None:
            return self._mssql_dsn
        raw = os.environ.get(self._MSSQL_DSN_ENV_VAR)
        return raw if raw and raw.strip() else None

    def mssql_host(self) -> str:
        """Return the SQL Server host (defaults to ``localhost``)."""
        if self._mssql_host is not None:
            return self._mssql_host
        raw = os.environ.get(self._MSSQL_HOST_ENV_VAR)
        return raw.strip() if raw and raw.strip() else self._DEFAULT_MSSQL_HOST

    def mssql_port(self) -> int:
        """Return the SQL Server port (defaults to ``1433``)."""
        if self._mssql_port is not None:
            return self._mssql_port
        raw = os.environ.get(self._MSSQL_PORT_ENV_VAR)
        if raw is None or not raw.strip():
            return self._DEFAULT_MSSQL_PORT
        return int(raw)

    def mssql_db(self) -> str | None:
        """Return the SQL Server database name when configured, else ``None``."""
        if self._mssql_db is not None:
            return self._mssql_db
        raw = os.environ.get(self._MSSQL_DB_ENV_VAR)
        return raw.strip() if raw and raw.strip() else None

    def mssql_user(self) -> str | None:
        """Return the SQL Server user when configured, else ``None``."""
        if self._mssql_user is not None:
            return self._mssql_user
        raw = os.environ.get(self._MSSQL_USER_ENV_VAR)
        return raw.strip() if raw and raw.strip() else None

    def mssql_password(self) -> str | None:
        """Return the SQL Server password when configured, else ``None``."""
        if self._mssql_password is not None:
            return self._mssql_password
        raw = os.environ.get(self._MSSQL_PASSWORD_ENV_VAR)
        return raw if raw and raw.strip() else None
