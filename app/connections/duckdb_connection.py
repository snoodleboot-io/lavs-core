"""DuckDB connection implementation."""

import contextlib
from collections.abc import Generator

import duckdb

from app.configurations.configuration import Configuration
from app.connections.connection import Connection


class DuckDBConnection(Connection):
    """DuckDB database connection implementation."""

    def __init__(self, config: Configuration | None = None) -> None:
        """Initialize the DuckDB connection.

        Args:
            config: Optional Configuration object. If not provided,
                   uses the default Configuration instance.
        """
        self._config = config or Configuration()

    @contextlib.contextmanager
    def connection(self) -> Generator[object]:
        """Generates and yields a live DuckDB connection.

        Uses the database path from the configuration, which reads
        from database.yaml.

        Yields:
            A DuckDB connection object.
        """
        connection = None
        try:
            db_path = self._config.database_path
            connection = duckdb.connect(db_path)
            yield connection
        finally:
            if connection:
                connection.close()
