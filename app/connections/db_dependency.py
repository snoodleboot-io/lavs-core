"""FastAPI dependency exposing the application-managed DuckDB connection.

This lives in its own module so resource routers can ``Depends`` on the live
connection without importing :mod:`app.main` (which would create an import
cycle: ``main`` imports the routers, and the routers would import ``main``).
"""

import duckdb
from fastapi import Request


def get_db_connection(request: Request) -> duckdb.DuckDBPyConnection:
    """Return the application-managed DuckDB connection.

    Args:
        request: The incoming request, used to reach ``app.state``.

    Returns:
        The live DuckDB connection managed by the application lifespan.
    """
    connection: duckdb.DuckDBPyConnection = request.app.state.db_connection
    return connection
