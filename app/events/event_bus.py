"""An in-process async pub/sub bus for per-product domain events.

The bus fans a published :class:`DomainEvent` out to every subscriber queue
registered for that event's ``product_id``. It is asyncio-only (no external
broker, no new dependency) and lives for the application's lifespan: it is
created in the FastAPI lifespan and stored on ``app.state.event_bus``.

Concurrency: all mutation of the subscriber registry happens in synchronous
methods with no ``await`` between read and write, so the single-threaded event
loop already serialises them; publishing uses :meth:`asyncio.Queue.put_nowait`
on unbounded queues, which never blocks and so never yields mid-fan-out.
"""

import asyncio

from app.events.domain_event import DomainEvent


class EventBus:
    """Per-product fan-out of domain events to subscriber queues."""

    def __init__(self) -> None:
        """Create an event bus with no subscribers."""
        self._subscribers: dict[str, set[asyncio.Queue[DomainEvent]]] = {}

    async def publish(self, event: DomainEvent) -> None:
        """Deliver ``event`` to every queue subscribed to its product.

        Delivery is non-blocking: each subscriber has an unbounded queue, so a
        slow or disconnected consumer cannot stall the publisher. Products with
        no subscribers are a no-op.

        Args:
            event: The domain event to fan out.
        """
        for queue in tuple(self._subscribers.get(event.product_id, ())):
            queue.put_nowait(event)

    def subscribe(self, product_id: str) -> asyncio.Queue[DomainEvent]:
        """Register and return a fresh queue for ``product_id``'s events.

        The caller consumes the queue with ``await queue.get()`` and must call
        :meth:`unsubscribe` (for example, on client disconnect) to release it.

        Args:
            product_id: The product whose events the caller wants.

        Returns:
            A new unbounded queue that will receive that product's events.
        """
        queue: asyncio.Queue[DomainEvent] = asyncio.Queue()
        self._subscribers.setdefault(product_id, set()).add(queue)
        return queue

    def unsubscribe(self, product_id: str, queue: asyncio.Queue[DomainEvent]) -> None:
        """Remove ``queue`` from ``product_id``'s subscribers.

        Idempotent: unsubscribing an already-removed queue (or an unknown
        product) is a no-op. The product's entry is dropped once its last
        subscriber leaves so the registry does not leak.

        Args:
            product_id: The product the queue was subscribed to.
            queue: The queue returned by :meth:`subscribe`.
        """
        subscribers = self._subscribers.get(product_id)
        if subscribers is None:
            return
        subscribers.discard(queue)
        if not subscribers:
            del self._subscribers[product_id]

    def subscriber_count(self, product_id: str) -> int:
        """Return how many active subscribers ``product_id`` currently has.

        Args:
            product_id: The product to count subscribers for.

        Returns:
            The number of live subscriber queues; ``0`` when none.
        """
        return len(self._subscribers.get(product_id, ()))
