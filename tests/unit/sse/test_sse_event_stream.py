"""Unit tests driving the SSE event-stream async generator directly.

These exercise the generator against a real :class:`EventBus` (no HTTP), which
keeps them deterministic: a short keep-alive interval lets the first idle poll
subscribe and emit a keep-alive before events are published, after which
published events surface as frames and closing the generator unsubscribes.
"""

from unittest import IsolatedAsyncioTestCase

from app.events.domain_event import DomainEvent
from app.events.event_bus import EventBus
from app.events.event_type import EventType
from app.sse.sse_event_stream import sse_event_stream
from app.sse.sse_formatter import format_sse_frame, keep_alive_frame

PRODUCT_ID = "01AAAAAAAAAAAAAAAAAAAAAAAA"
OTHER_PRODUCT = "01BBBBBBBBBBBBBBBBBBBBBBBB"
COMPONENT_ID = "01CCCCCCCCCCCCCCCCCCCCCCCC"


def _event(product_id: str = PRODUCT_ID) -> DomainEvent:
    """Build a representative ``version.created`` event for a product."""
    return DomainEvent(
        event_type=EventType.VERSION_CREATED,
        product_id=product_id,
        data={"component_id": COMPONENT_ID, "version": {"major": 1, "minor": 0, "patch": 0}},
    )


class TestSseEventStream(IsolatedAsyncioTestCase):
    """Subscription, framing, keep-alive, and disconnect cleanup."""

    async def test_idle_stream_yields_keep_alive_comment(self) -> None:
        """With no events, the first poll times out and yields a keep-alive."""
        # Arrange
        bus = EventBus()
        stream = sse_event_stream(bus, PRODUCT_ID, keep_alive_seconds=0.01)

        # Act
        frame = await stream.__anext__()

        # Assert
        assert frame == keep_alive_frame()
        await stream.aclose()

    async def test_published_event_is_yielded_as_a_frame(self) -> None:
        """An event published after subscription surfaces as its SSE frame."""
        # Arrange
        bus = EventBus()
        stream = sse_event_stream(bus, PRODUCT_ID, keep_alive_seconds=0.01)
        _ = await stream.__anext__()  # first idle poll subscribes the stream
        event = _event()

        # Act
        await bus.publish(event)
        frame = await stream.__anext__()

        # Assert
        assert frame == format_sse_frame(event)
        await stream.aclose()

    async def test_stream_only_sees_its_products_events(self) -> None:
        """An event for another product does not surface on this stream."""
        # Arrange
        bus = EventBus()
        stream = sse_event_stream(bus, PRODUCT_ID, keep_alive_seconds=0.01)
        _ = await stream.__anext__()  # subscribe

        # Act
        await bus.publish(_event(OTHER_PRODUCT))
        frame = await stream.__anext__()

        # Assert
        assert frame == keep_alive_frame()
        await stream.aclose()

    async def test_closing_the_stream_unsubscribes(self) -> None:
        """Closing the generator releases the subscriber queue (no leak)."""
        # Arrange
        bus = EventBus()
        stream = sse_event_stream(bus, PRODUCT_ID, keep_alive_seconds=0.01)
        _ = await stream.__anext__()  # subscribe
        assert bus.subscriber_count(PRODUCT_ID) == 1

        # Act
        await stream.aclose()

        # Assert
        assert bus.subscriber_count(PRODUCT_ID) == 0
