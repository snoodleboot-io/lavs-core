import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import duckdb
import uvicorn
from fastapi import FastAPI, Request, Response

from app.connections.connection_factory import ConnectionFactory
from app.routers import basic_crud, patch, versions

logger = logging.getLogger("lavs-api")


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Manage a single DuckDB connection for the application lifetime.

    Opens one managed DuckDB connection at startup via the connection
    factory context manager and closes it automatically at shutdown. The
    live connection is exposed on ``application.state.db_connection`` so
    request handlers and dependencies can reuse it.
    """
    with ConnectionFactory().connect(key="duckdb") as connection:
        application.state.db_connection = connection
        logger.info("Managed DuckDB connection opened for application lifespan.")
        try:
            yield
        finally:
            application.state.db_connection = None
            logger.info("Managed DuckDB connection closed for application lifespan.")


app = FastAPI(lifespan=lifespan)


def get_db_connection(request: Request) -> duckdb.DuckDBPyConnection:
    """Return the application-managed DuckDB connection.

    Args:
        request: The incoming request, used to reach ``app.state``.

    Returns:
        The live DuckDB connection managed by the application lifespan.
    """
    connection: duckdb.DuckDBPyConnection = request.app.state.db_connection
    return connection


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


app.include_router(patch.router)
app.include_router(basic_crud.router)
app.include_router(versions.router)

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="localhost", port=8001)
