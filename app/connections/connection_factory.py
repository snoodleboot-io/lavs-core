"""Connection factory for creating database connections.

This factory supports multiple database backends and allows configuration
to be passed for customizing connection behavior.
"""

import contextlib
from collections.abc import Generator

from app.configurations.configuration import Configuration
from app.connections.connection import Connection
from app.connections.duckdb_connection import DuckDBConnection


class ConnectionFactory:
    """Factory for creating database connections.

    Supports multiple database backends (currently only DuckDB).
    Configuration can be passed to customize connection behavior.
    """

    _registry: dict[str, type[Connection]] = {"duckdb": DuckDBConnection}

    def __init__(self, config: Configuration | None = None) -> None:
        """Initialize the connection factory.

        Args:
            config: Optional Configuration object. If not provided,
                   uses the default Configuration instance.
        """
        self._config = config or Configuration()

    @classmethod
    def register_backend(cls, name: str, connection_class: type[Connection]) -> None:
        """Register a new database backend.

        Args:
            name: Identifier for the backend (e.g., "duckdb", "postgresql").
            connection_class: Connection class implementation.
        """
        cls._registry[name] = connection_class

    @contextlib.contextmanager
    def retrieve(self, key: str) -> Generator[Connection]:
        """Retrieve a connection for the specified backend.

        Args:
            key: Identifier for the backend to use.

        Yields:
            Connection: A connection object for the specified backend.

        Raises:
            ValueError: When the key is not a valid backend identifier.
        """
        if key not in self._registry:
            raise ValueError(
                f"Unknown database backend: {key}. Available: {list(self._registry.keys())}"
            )

        connection_class = self._registry[key]
        # Pass configuration to the connection
        with connection_class(self._config).connection() as conn:  # type: ignore[reportGeneralTypeIssues]
            yield conn

    @contextlib.contextmanager
    def connect(self, key: str = "duckdb") -> Generator[object]:
        """Convenience method to get a raw database connection.

        This is a shortcut for retrieving the connection and yielding
        the raw database connection object.

        Args:
            key: Identifier for the backend (default: "duckdb").

        Yields:
            The raw database connection object.
        """
        with self.retrieve(key) as conn:
            yield conn


# Module-level factory instance for backwards compatibility
_default_factory = ConnectionFactory()


def get_connection(key: str = "duckdb") -> Generator[object]:
    """Get a database connection using the default factory.

    This is a convenience function for simple use cases.

    Args:
        key: Identifier for the backend (default: "duckdb").

    Yields:
        The raw database connection object.

    Raises:
        ValueError: When the key is not a valid backend identifier.
    """
    with _default_factory.connect(key) as conn:
        yield conn
