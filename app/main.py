import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request, Response

from app.auth.auth_resolver_factory import AuthResolverFactory
from app.auth.auth_settings import AuthSettings
from app.auth.providers.password_session_provider import PasswordSessionProvider
from app.backends.backend_factory import BackendFactory
from app.connections.db_session import DbSession
from app.database.migration.flat_to_relational_migration import FlatToRelationalMigration
from app.errors.handlers import register_error_handlers
from app.events.event_bus import EventBus
from app.mail.capture_mailer import CaptureMailer
from app.routers import auth, components, events, meta, products, releases, timeline, versions

logger = logging.getLogger("lavs-api")


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Manage a single database session and initialise the schema.

    On startup this builds the configured backend (``LAVS_DB_BACKEND``, DuckDB
    by default) via :class:`BackendFactory`, opens one managed
    :class:`DbSession`, materialises the schema through
    ``backend.init_schema`` (idempotent), and runs the idempotent
    flat-to-relational migration before serving traffic. The live session is
    exposed on ``application.state.db_connection`` so request
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
    backend = BackendFactory().create()
    with backend.connect() as session:
        application.state.db_connection = session
        application.state.event_bus = EventBus()

        auth_settings = AuthSettings()
        auth_registry = AuthResolverFactory.build_registry(auth_settings)
        if auth_settings.password_enabled():
            auth_registry.register(PasswordSessionProvider(edition=auth_settings.edition()))
        application.state.auth_settings = auth_settings
        application.state.auth_registry = auth_registry
        application.state.auth_resolver = AuthResolverFactory.build_resolver(
            auth_settings, registry=auth_registry
        )
        application.state.mailer = CaptureMailer()

        logger.info("Managed %s session opened for application lifespan.", backend.name.value)
        backend.init_schema(session)
        FlatToRelationalMigration().run(session)
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
            logger.info("Managed database session closed for application lifespan.")


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
    connection: DbSession | None = request.app.state.db_connection
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
