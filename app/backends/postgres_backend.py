"""The PostgreSQL persistence backend — the networked, concurrent target.

``PostgresBackend`` mirrors :class:`~app.backends.duckdb_backend.DuckDBBackend`
behind the same :class:`~app.backends.backend.Backend` contract, differing only
in the driver (psycopg), the placeholder style (pyformat ``%s``), and two
dialect accommodations:

* :meth:`connect` opens the connection with ``autocommit`` enabled so a write is
  visible to the next statement without an explicit ``commit`` — matching the
  effective visibility DuckDB gives the query layer, whose callers never commit.
* :meth:`init_schema` splits the DDL into single statements because psycopg,
  over the extended-query protocol, rejects a multi-statement ``execute``.
"""

import contextlib
import os
from collections.abc import Generator
from typing import Any

import psycopg

from app.backends.backend import Backend
from app.backends.backend_kind import BackendKind
from app.backends.backend_settings import BackendSettings
from app.backends.ddl_script import DdlScript
from app.connections.db_session import DbSession
from app.connections.param_style import ParamStyle


class PostgresBackend(Backend):
    """psycopg-backed PostgreSQL backend using pyformat (``%s``) placeholders."""

    #: The dialect DDL script, relative to the ``app/database`` package.
    _DDL_RELATIVE_PATH: str = "postgres/ddl.sql"

    def __init__(self, settings: BackendSettings | None = None) -> None:
        """Initialise the backend.

        Args:
            settings: The backend settings supplying the connection parameters
                (DSN or discrete host/port/db/user/password). Defaults to
                settings read from the environment.
        """
        self._settings = settings or BackendSettings()

    @property
    def name(self) -> BackendKind:
        """Return :attr:`BackendKind.POSTGRES`."""
        return BackendKind.POSTGRES

    @property
    def param_style(self) -> ParamStyle:
        """Return :attr:`ParamStyle.PYFORMAT` — psycopg's placeholder style."""
        return ParamStyle.PYFORMAT

    @contextlib.contextmanager
    def connect(self) -> Generator[DbSession]:
        """Open a psycopg connection wrapped in a :class:`DbSession`.

        The connection is opened from the configured DSN (preferred) or the
        discrete host/port/db/user/password fields, put into ``autocommit`` mode
        so writes are immediately visible to later reads (matching DuckDB's
        effective behaviour for the commit-free query layer), and closed when the
        context exits.

        Yields:
            A live :class:`DbSession` over the psycopg connection.
        """
        connection = psycopg.connect(**self._connection_kwargs())
        try:
            connection.autocommit = True
            yield DbSession(connection, self.param_style)
        finally:
            connection.close()

    def init_schema(self, session: DbSession) -> None:
        """Materialise the schema by running each DDL statement individually.

        psycopg rejects a multi-statement ``execute`` over the extended-query
        protocol, so the script is split and each statement is executed in turn.
        Every statement is idempotent (``CREATE TABLE IF NOT EXISTS`` /
        ``ADD COLUMN IF NOT EXISTS``), so this is safe to run on every boot.

        Args:
            session: A live session to run the DDL on.
        """
        for statement in DdlScript(self.dialect_ddl()).statements():
            session.execute(statement)

    def dialect_ddl(self) -> str:
        """Return the PostgreSQL DDL script contents."""
        database_package = os.path.dirname(os.path.dirname(__file__))
        ddl_path = os.path.join(database_package, "database", self._DDL_RELATIVE_PATH)
        with open(ddl_path, encoding="utf-8") as stream:
            return stream.read()

    def _connection_kwargs(self) -> dict[str, Any]:
        """Build the psycopg connection keyword arguments from the settings.

        A configured DSN supersedes the discrete fields entirely; otherwise the
        host, port, database, user, and password are supplied individually, each
        omitted when unset so psycopg falls back to its libpq defaults.

        Returns:
            The keyword arguments for :func:`psycopg.connect`.
        """
        dsn = self._settings.pg_dsn()
        if dsn is not None:
            return {"conninfo": dsn}

        kwargs: dict[str, Any] = {
            "host": self._settings.pg_host(),
            "port": self._settings.pg_port(),
        }
        database = self._settings.pg_db()
        if database is not None:
            kwargs["dbname"] = database
        user = self._settings.pg_user()
        if user is not None:
            kwargs["user"] = user
        password = self._settings.pg_password()
        if password is not None:
            kwargs["password"] = password
        return kwargs
