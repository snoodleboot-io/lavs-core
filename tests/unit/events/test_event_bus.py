"""Unit tests for the in-process :class:`EventBus`."""

from unittest import IsolatedAsyncioTestCase

from app.events.domain_event import DomainEvent
from app.events.event_bus import EventBus
from app.events.event_type import EventType

PRODUCT_A = "01AAAAAAAAAAAAAAAAAAAAAAAA"
PRODUCT_B = "01BBBBBBBBBBBBBBBBBBBBBBBB"


def _event(product_id: str, component_id: str = "01CCCCCCCCCCCCCCCCCCCCCCCC") -> DomainEvent:
    """Build a representative ``version.created`` event for a product."""
    return DomainEvent(
        event_type=EventType.VERSION_CREATED,
        product_id=product_id,
        data={"component_id": component_id, "version": {"major": 1, "minor": 0, "patch": 0}},
    )


class TestEventBus(IsolatedAsyncioTestCase):
    """Publish/subscribe fan-out, isolation, and cleanup."""

    async def test_subscriber_receives_published_event(self) -> None:
        """A published event reaches a queue subscribed to its product."""
        # Arrange
        bus = EventBus()
        queue = bus.subscribe(PRODUCT_A)
        event = _event(PRODUCT_A)

        # Act
        await bus.publish(event)

        # Assert
        assert queue.get_nowait() is event

    async def test_all_subscribers_of_a_product_receive_the_event(self) -> None:
        """Every subscriber of a product receives its own copy of the event."""
        # Arrange
        bus = EventBus()
        first = bus.subscribe(PRODUCT_A)
        second = bus.subscribe(PRODUCT_A)
        event = _event(PRODUCT_A)

        # Act
        await bus.publish(event)

        # Assert
        assert first.get_nowait() is event
        assert second.get_nowait() is event

    async def test_events_are_isolated_per_product(self) -> None:
        """A subscriber only sees events published for its own product."""
        # Arrange
        bus = EventBus()
        queue_a = bus.subscribe(PRODUCT_A)
        queue_b = bus.subscribe(PRODUCT_B)

        # Act
        await bus.publish(_event(PRODUCT_A))

        # Assert
        assert queue_a.qsize() == 1
        assert queue_b.empty()

    async def test_publish_with_no_subscribers_is_a_noop(self) -> None:
        """Publishing to a product without subscribers does not raise."""
        # Arrange
        bus = EventBus()

        # Act / Assert
        await bus.publish(_event(PRODUCT_A))
        assert bus.subscriber_count(PRODUCT_A) == 0

    async def test_unsubscribe_stops_delivery(self) -> None:
        """An unsubscribed queue no longer receives events."""
        # Arrange
        bus = EventBus()
        queue = bus.subscribe(PRODUCT_A)

        # Act
        bus.unsubscribe(PRODUCT_A, queue)
        await bus.publish(_event(PRODUCT_A))

        # Assert
        assert queue.empty()

    async def test_unsubscribe_last_subscriber_clears_product_entry(self) -> None:
        """Removing the final subscriber drops the product from the registry."""
        # Arrange
        bus = EventBus()
        queue = bus.subscribe(PRODUCT_A)

        # Act
        bus.unsubscribe(PRODUCT_A, queue)

        # Assert
        assert bus.subscriber_count(PRODUCT_A) == 0

    async def test_unsubscribe_is_idempotent(self) -> None:
        """Unsubscribing an already-removed queue is a safe no-op."""
        # Arrange
        bus = EventBus()
        queue = bus.subscribe(PRODUCT_A)
        bus.unsubscribe(PRODUCT_A, queue)

        # Act / Assert
        bus.unsubscribe(PRODUCT_A, queue)
        bus.unsubscribe("01ZZZZZZZZZZZZZZZZZZZZZZZZ", queue)

    async def test_one_subscriber_leaving_does_not_affect_another(self) -> None:
        """Unsubscribing one queue leaves a sibling subscriber delivering."""
        # Arrange
        bus = EventBus()
        staying = bus.subscribe(PRODUCT_A)
        leaving = bus.subscribe(PRODUCT_A)

        # Act
        bus.unsubscribe(PRODUCT_A, leaving)
        await bus.publish(_event(PRODUCT_A))

        # Assert
        assert staying.qsize() == 1
        assert leaving.empty()
        assert bus.subscriber_count(PRODUCT_A) == 1
