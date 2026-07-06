import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import duckdb
import uvicorn
from fastapi import FastAPI, Request, Response

from app.connections.connection_factory import ConnectionFactory
from app.database.database_manager import DatabaseManager
from app.database.migration.flat_to_relational_migration import FlatToRelationalMigration
from app.errors.handlers import register_error_handlers
from app.routers import components, products, timeline, versions

logger = logging.getLogger("lavs-api")


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Manage a single DuckDB connection and initialise the schema.

    On startup this opens one managed DuckDB connection via the connection
    factory, ensures the configured tables exist (idempotent), and runs the
    idempotent flat-to-relational migration before serving traffic. The live
    connection is exposed on ``application.state.db_connection`` so request
    handlers and dependencies can reuse it, and is closed automatically at
    shutdown.
    """
    with ConnectionFactory().connect(key="duckdb") as raw_connection:
        if not isinstance(raw_connection, duckdb.DuckDBPyConnection):
            raise TypeError("The duckdb backend must yield a DuckDBPyConnection.")
        connection = raw_connection
        application.state.db_connection = connection
        logger.info("Managed DuckDB connection opened for application lifespan.")
        DatabaseManager.create_tables()
        FlatToRelationalMigration().run(connection)
        logger.info("Schema initialised and migration applied.")
        try:
            yield
        finally:
            application.state.db_connection = None
            logger.info("Managed DuckDB connection closed for application lifespan.")


app = FastAPI(lifespan=lifespan)
register_error_handlers(app)


@app.get("/")
def root():
    logger.info("Welcome to the lowercase acronym versioning system.")
    return "Welcome to the lowercase acronym versioning system."


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe.

    Returns:
        A static payload indicating the process is up.
    """
    return {"status": "ok"}


@app.get("/ready")
def ready(response: Response, request: Request) -> dict[str, str]:
    """Readiness probe.

    Verifies the managed database answers a trivial ``SELECT 1`` query.

    Args:
        response: The outgoing response, used to set a 503 on failure.
        request: The incoming request, used to reach the managed connection.

    Returns:
        A payload describing readiness state.
    """
    connection: duckdb.DuckDBPyConnection | None = request.app.state.db_connection
    if connection is None:
        response.status_code = 503
        return {"status": "not ready"}

    try:
        connection.execute("SELECT 1").fetchone()
    except Exception:
        logger.exception("Readiness check failed: database did not answer SELECT 1.")
        response.status_code = 503
        return {"status": "not ready"}

    return {"status": "ready"}


app.include_router(products.router)
app.include_router(components.router)
app.include_router(versions.router)
app.include_router(timeline.router)

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="localhost", port=8001)
