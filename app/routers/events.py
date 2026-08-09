"""Router shell for the Server-Sent Events stream.

Carries no prefix; the SSE lane adds ``GET /products/{id}/events`` (a
``text/event-stream`` response, see ``docs/design/API_CONTRACT.md`` §6) on the
shared ``router`` below, which fixes the tag and the mandatory authenticated-principal
dependency so auth is enforced uniformly.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.auth.require_principal import require_principal
from app.events.event_bus import EventBus
from app.events.event_bus_dependency import get_event_bus
from app.sse.sse_event_stream import sse_event_stream

router = APIRouter(
    tags=["events"],
    dependencies=[Depends(require_principal)],
)

Bus = Annotated[EventBus, Depends(get_event_bus)]

_SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


@router.get("/products/{product_id}/events")
async def stream_product_events(product_id: str, event_bus: Bus) -> StreamingResponse:
    """Open a ``text/event-stream`` of one product's live domain events.

    The response streams SSE frames (``version.created``, ``version.rolled_back``,
    ``release.cut`` per ``docs/design/API_CONTRACT.md`` §6) as they are published
    on the shared event bus, interleaved with periodic keep-alive comments. The
    connection stays open until the client disconnects, at which point the
    underlying generator unsubscribes from the bus.

    Args:
        product_id: The product whose event stream the client is subscribing to.
        event_bus: The application-managed event bus (injected).

    Returns:
        A streaming response with media type ``text/event-stream``.
    """
    return StreamingResponse(
        sse_event_stream(event_bus, product_id),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )
