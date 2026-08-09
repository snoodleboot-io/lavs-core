"""FastAPI dependency exposing the application-managed database session.

This lives in its own module so resource routers can ``Depends`` on the live
session without importing :mod:`app.main` (which would create an import cycle:
``main`` imports the routers, and the routers would import ``main``).
"""

from fastapi import Request

from app.connections.db_session import DbSession


def get_db_connection(request: Request) -> DbSession:
    """Return the application-managed database session.

    Args:
        request: The incoming request, used to reach ``app.state``.

    Returns:
        The live :class:`DbSession` managed by the application lifespan.
    """
    connection: DbSession = request.app.state.db_connection
    return connection
