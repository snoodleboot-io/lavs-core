"""The DuckDB persistence backend — the local/test default."""

import contextlib
import os
from collections.abc import Generator

import duckdb

from app.backends.backend import Backend
from app.backends.backend_kind import BackendKind
from app.configurations.configuration import Configuration
from app.connections.db_session import DbSession
from app.connections.param_style import ParamStyle


class DuckDBBackend(Backend):
    """File-based DuckDB backend using native ``?`` (qmark) placeholders."""

    #: The dialect DDL script, relative to the ``app/database`` package.
    _DDL_RELATIVE_PATH: str = "duckdb/ddl.sql"

    def __init__(self, config: Configuration | None = None) -> None:
        """Initialise the backend.

        Args:
            config: Optional configuration supplying the database path. Defaults
                to the process configuration read from ``database.yaml``.
        """
        self._config = config or Configuration()

    @property
    def name(self) -> BackendKind:
        """Return :attr:`BackendKind.DUCKDB`."""
        return BackendKind.DUCKDB

    @property
    def param_style(self) -> ParamStyle:
        """Return :attr:`ParamStyle.QMARK` — DuckDB's native placeholder style."""
        return ParamStyle.QMARK

    @contextlib.contextmanager
    def connect(self) -> Generator[DbSession]:
        """Open a DuckDB connection wrapped in a :class:`DbSession`.

        The connection is opened against the configured database path and closed
        when the context exits.

        Yields:
            A live :class:`DbSession` over the DuckDB connection.
        """
        connection = duckdb.connect(self._config.database_path)
        try:
            yield DbSession(connection, self.param_style)
        finally:
            connection.close()

    def dialect_ddl(self) -> str:
        """Return the DuckDB DDL script contents."""
        database_package = os.path.dirname(os.path.dirname(__file__))
        ddl_path = os.path.join(database_package, "database", self._DDL_RELATIVE_PATH)
        with open(ddl_path, encoding="utf-8") as stream:
            return stream.read()
