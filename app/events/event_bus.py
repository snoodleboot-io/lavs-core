"""An in-process async pub/sub bus for per-product domain events.

The bus fans a published :class:`DomainEvent` out to every subscriber queue
registered for that event's ``product_id``. It is asyncio-only (no external
broker, no new dependency) and lives for the application's lifespan: it is
created in the FastAPI lifespan and stored on ``app.state.event_bus``.

Concurrency: all mutation of the subscriber registry happens in synchronous
methods with no ``await`` between read and write, so the single-threaded event
loop already serialises them; publishing uses :meth:`asyncio.Queue.put_nowait`
(with synchronous drop-oldest eviction on overflow), which never blocks and so
never yields mid-fan-out.

Backpressure policy: each subscriber queue is bounded (:data:`QUEUE_MAXSIZE`).
When a slow or stalled consumer lets its queue fill up, the oldest queued event
is evicted to make room for the newest — the publisher never blocks and never
raises. A consumer that missed events simply re-syncs the full state via the
REST endpoints (SSE frames are notifications, not the source of truth), so
dropping stale frames is safe.
"""

import asyncio

from app.events.domain_event import DomainEvent

QUEUE_MAXSIZE = 256
"""Per-subscriber queue bound; overflow evicts the oldest queued event."""


class EventBus:
    """Per-product fan-out of domain events to bounded subscriber queues."""

    def __init__(self) -> None:
        """Create an event bus with no subscribers."""
        self._subscribers: dict[str, set[asyncio.Queue[DomainEvent]]] = {}

    async def publish(self, event: DomainEvent) -> None:
        """Deliver ``event`` to every queue subscribed to its product.

        Delivery is non-blocking and never raises: each subscriber queue is
        bounded, and when one is full the oldest queued event is dropped to
        make room for this one (drop-oldest). A slow or disconnected consumer
        therefore cannot stall the publisher; it re-syncs via REST after a
        gap. Products with no subscribers are a no-op.

        Args:
            event: The domain event to fan out.
        """
        for queue in tuple(self._subscribers.get(event.product_id, ())):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                self._evict_oldest_and_put(queue, event)

    @staticmethod
    def _evict_oldest_and_put(queue: asyncio.Queue[DomainEvent], event: DomainEvent) -> None:
        """Drop the oldest queued event, then enqueue ``event``.

        Runs synchronously with no ``await``, so no consumer can interleave
        between the eviction and the put on the single-threaded event loop.
        Both fallbacks are defensive: after evicting one item from a full
        bounded queue the put cannot fail, and an empty queue cannot be full.

        Args:
            queue: The full subscriber queue to make room in.
            event: The new event to enqueue after eviction.
        """
        try:
            queue.get_nowait()
        except asyncio.QueueEmpty:  # pragma: no cover - full queue is never empty
            pass
        try:
            queue.put_nowait(event)
        except asyncio.QueueFull:  # pragma: no cover - room was just made above
            pass

    def subscribe(self, product_id: str) -> asyncio.Queue[DomainEvent]:
        """Register and return a fresh queue for ``product_id``'s events.

        The caller consumes the queue with ``await queue.get()`` and must call
        :meth:`unsubscribe` (for example, on client disconnect) to release it.

        Args:
            product_id: The product whose events the caller wants.

        Returns:
            A new bounded queue (:data:`QUEUE_MAXSIZE`) that will receive that
            product's events; on overflow its oldest event is dropped.
        """
        queue: asyncio.Queue[DomainEvent] = asyncio.Queue(maxsize=QUEUE_MAXSIZE)
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
