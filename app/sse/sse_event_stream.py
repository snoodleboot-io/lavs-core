"""The async generator backing a product's live Server-Sent Events response.

The generator subscribes to the shared :class:`EventBus` for one product,
yields each fanned-out event as an SSE frame, and emits a keep-alive comment
whenever the stream is idle for ``keep_alive_seconds``. It always unsubscribes
in a ``finally`` block, so a client disconnect (which closes the generator)
releases the subscriber queue and never leaks a registration.
"""

import asyncio
from collections.abc import AsyncIterator

from app.events.event_bus import EventBus
from app.sse.sse_formatter import format_sse_frame, keep_alive_frame

_DEFAULT_KEEP_ALIVE_SECONDS = 15.0


async def sse_event_stream(
    event_bus: EventBus,
    product_id: str,
    keep_alive_seconds: float = _DEFAULT_KEEP_ALIVE_SECONDS,
) -> AsyncIterator[str]:
    """Yield SSE frames for ``product_id`` until the consumer stops iterating.

    Subscribes to ``event_bus`` for the product, then loops: it waits up to
    ``keep_alive_seconds`` for the next event and yields its formatted frame; on
    idle timeout it yields a keep-alive comment instead. When the consumer (the
    HTTP response) is closed on client disconnect, the generator's ``finally``
    unsubscribes the queue so no subscriber leaks.

    Args:
        event_bus: The application-scoped event bus to subscribe to.
        product_id: The product whose events this stream carries.
        keep_alive_seconds: Idle interval after which a keep-alive comment is
            emitted to detect dead clients.

    Yields:
        SSE wire frames (event frames interleaved with keep-alive comments).
    """
    queue = event_bus.subscribe(product_id)
    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=keep_alive_seconds)
            except TimeoutError:
                yield keep_alive_frame()
                continue
            yield format_sse_frame(event)
    finally:
        event_bus.unsubscribe(product_id, queue)
