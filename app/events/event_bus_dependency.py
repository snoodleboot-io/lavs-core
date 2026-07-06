"""FastAPI dependency exposing the application-scoped event bus.

Mirrors :mod:`app.connections.db_dependency`: it lives in its own module so the
SSE and cut-release routers can ``Depends`` on the shared
:class:`~app.events.event_bus.EventBus` without importing :mod:`app.main` (which
imports the routers, so the reverse import would cycle). The single instance is
created in the application lifespan and stored on ``app.state.event_bus``.
"""

from fastapi import Request

from app.events.event_bus import EventBus


def get_event_bus(request: Request) -> EventBus:
    """Return the application-managed event bus.

    Args:
        request: The incoming request, used to reach ``app.state``.

    Returns:
        The live :class:`EventBus` created by the application lifespan.
    """
    event_bus: EventBus = request.app.state.event_bus
    return event_bus
