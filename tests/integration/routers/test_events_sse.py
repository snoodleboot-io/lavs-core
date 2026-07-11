"""Integration tests for the SSE endpoint handler.

The endpoint is exercised by invoking its route function directly against a real
:class:`EventBus`, rather than over an HTTP stream: the ``TestClient`` transport
buffers a response body to completion, which would never return for an
open-ended event stream. Calling the handler still exercises the real router
function, the streaming response wiring, and the generator's subscribe/frame
behaviour, while staying deterministic. Delivery correctness is covered further
by the generator unit tests and the version-emission integration tests.
"""

import asyncio
from unittest import IsolatedAsyncioTestCase

from app.events.domain_event import DomainEvent
from app.events.event_bus import EventBus
from app.events.event_type import EventType
from app.routers.events import stream_product_events
from app.sse.sse_formatter import format_sse_frame

PRODUCT_ID = "01AAAAAAAAAAAAAAAAAAAAAAAA"
COMPONENT_ID = "01CCCCCCCCCCCCCCCCCCCCCCCC"


class TestStreamProductEvents(IsolatedAsyncioTestCase):
    """Media type, streaming headers, and subscription of the SSE endpoint."""

    async def test_response_is_event_stream_with_streaming_headers(self) -> None:
        """The handler returns a ``text/event-stream`` with no-buffer headers."""
        # Arrange
        bus = EventBus()

        # Act
        response = await stream_product_events(PRODUCT_ID, bus)

        # Assert
        assert response.media_type == "text/event-stream"
        assert response.headers["cache-control"] == "no-cache"
        assert response.headers["connection"] == "keep-alive"
        assert response.headers["x-accel-buffering"] == "no"
        await response.body_iterator.aclose()

    async def test_stream_body_subscribes_and_frames_events(self) -> None:
        """Iterating the response body subscribes the product and frames events."""
        # Arrange
        bus = EventBus()
        response = await stream_product_events(PRODUCT_ID, bus)
        body = response.body_iterator
        event = DomainEvent(
            event_type=EventType.VERSION_CREATED,
            product_id=PRODUCT_ID,
            data={"component_id": COMPONENT_ID, "version": {"major": 1}},
        )

        # Act
        pending = asyncio.ensure_future(body.__anext__())
        while bus.subscriber_count(PRODUCT_ID) == 0:  # let the generator subscribe first
            await asyncio.sleep(0)
        await bus.publish(event)
        frame = await pending

        # Assert
        assert bus.subscriber_count(PRODUCT_ID) == 1
        assert frame == format_sse_frame(event)
        await body.aclose()
        assert bus.subscriber_count(PRODUCT_ID) == 0
