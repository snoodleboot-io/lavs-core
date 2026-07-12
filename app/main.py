import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import duckdb
import uvicorn
from fastapi import FastAPI, Request, Response

from app.auth.auth_resolver_factory import AuthResolverFactory
from app.auth.auth_settings import AuthSettings
from app.connections.connection_factory import ConnectionFactory
from app.database.database_manager import DatabaseManager
from app.database.migration.flat_to_relational_migration import FlatToRelationalMigration
from app.errors.handlers import register_error_handlers
from app.events.event_bus import EventBus
from app.mail.capture_mailer import CaptureMailer
from app.routers import auth, components, events, meta, products, releases, timeline, versions

logger = logging.getLogger("lavs-api")


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Manage a single DuckDB connection and initialise the schema.

    On startup this opens one managed DuckDB connection via the connection
    factory, ensures the configured tables exist (idempotent), and runs the
    idempotent flat-to-relational migration before serving traffic. The live
    connection is exposed on ``application.state.db_connection`` so request
    handlers and dependencies can reuse it, and is closed automatically at
    shutdown. A single in-process :class:`EventBus` is created and exposed on
    ``application.state.event_bus`` for the SSE and cut-release lanes to share.

    The auth spine is also assembled here: :class:`AuthSettings` is read from the
    environment, an :class:`~app.auth.auth_registry.AuthRegistry` is populated
    with the enabled providers (the API-key provider today), and an
    :class:`~app.auth.auth_resolver.AuthResolver` over it is exposed on
    ``application.state.auth_resolver``. The registry itself is exposed on
    ``application.state.auth_registry`` so a later lane (R2's
    ``PasswordSessionProvider``) can register onto it — the resolver reads the
    registry live, so a provider added after startup still takes effect. A
    :class:`~app.mail.capture_mailer.CaptureMailer` is exposed on
    ``application.state.mailer`` as the deterministic email sink.
    """
    with ConnectionFactory().connect(key="duckdb") as raw_connection:
        if not isinstance(raw_connection, duckdb.DuckDBPyConnection):
            raise TypeError("The duckdb backend must yield a DuckDBPyConnection.")
        connection = raw_connection
        application.state.db_connection = connection
        application.state.event_bus = EventBus()

        auth_settings = AuthSettings()
        auth_registry = AuthResolverFactory.build_registry(auth_settings)
        application.state.auth_settings = auth_settings
        application.state.auth_registry = auth_registry
        application.state.auth_resolver = AuthResolverFactory.build_resolver(
            auth_settings, registry=auth_registry
        )
        application.state.mailer = CaptureMailer()

        logger.info("Managed DuckDB connection opened for application lifespan.")
        DatabaseManager.create_tables()
        FlatToRelationalMigration().run(connection)
        logger.info("Schema initialised and migration applied.")
        try:
            yield
        finally:
            application.state.db_connection = None
            application.state.event_bus = None
            application.state.auth_settings = None
            application.state.auth_registry = None
            application.state.auth_resolver = None
            application.state.mailer = None
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


app.include_router(meta.router)
app.include_router(auth.router)
app.include_router(products.router)
app.include_router(components.router)
app.include_router(versions.router)
app.include_router(timeline.router)
app.include_router(releases.router)
app.include_router(events.router)

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="localhost", port=8001)
