"""Acceptance: cutting a release publishes a ``release.cut`` event (P2, API_CONTRACT §6).

The intended HTTP contract is ``GET /products/{id}/events`` (``text/event-stream``)
delivering an ``event: release.cut`` frame whose ``data`` is ``{"release": {…}}``
the moment a release is cut (API_CONTRACT §6). In-process SSE streaming over the
FastAPI ``TestClient`` is not deterministic -- the endpoint blocks awaiting the
next event on a background event loop -- so the reliable, deterministic assertion
here is made at the **event-bus boundary**: cutting a release must ``publish`` a
``release.cut`` :class:`DomainEvent`, scoped to the product, carrying the release.
That publish is exactly what the SSE endpoint fans out to subscribers, so proving
it proves the stream's contract without a flaky socket read.

These tests drive the REAL HTTP cut endpoint through the ``TestClient``. Until the
release resource lane is merged the endpoint 404s and no event is published, so
these acceptance scenarios are expected to be RED.
"""

from collections.abc import Iterator

from fastapi.testclient import TestClient

from app.events.domain_event import DomainEvent
from app.events.event_type import EventType

_CREATED_OK = (200, 201)


def _seed_released_product(client: TestClient) -> str:
    """Create a product + component + active version and return the product id.

    Args:
        client: The FastAPI test client.

    Returns:
        The created product's id.
    """
    product = client.post("/products", json={"name": "Aurora Platform"})
    assert product.status_code in _CREATED_OK, product.text
    product_id = str(product.json()["id"])

    component = client.post(
        "/components", json={"product_id": product_id, "name": "lavs-api", "kind": "service"}
    )
    assert component.status_code in _CREATED_OK, component.text
    version = client.post(
        "/versions", json={"component_id": str(component.json()["id"]), "version": "2.4.0"}
    )
    assert version.status_code in _CREATED_OK, version.text
    return product_id


def _capture_published_events(client: TestClient) -> list[DomainEvent]:
    """Wrap the app's event bus ``publish`` to record every event it fans out.

    The application-scoped :class:`~app.events.event_bus.EventBus` lives on
    ``app.state.event_bus`` (created in the lifespan the ``client`` fixture
    enters). Shadowing its bound ``publish`` with a recording wrapper captures
    what the cut endpoint emits, independent of any SSE subscriber's event loop.

    Args:
        client: The FastAPI test client with an active lifespan.

    Returns:
        A list that accumulates each published :class:`DomainEvent`.
    """
    captured: list[DomainEvent] = []
    event_bus = client.app.state.event_bus
    original_publish = event_bus.publish

    async def recording_publish(event: DomainEvent) -> None:
        captured.append(event)
        await original_publish(event)

    event_bus.publish = recording_publish
    return captured


def _release_cut_events(events: list[DomainEvent], product_id: str) -> Iterator[DomainEvent]:
    """Yield the ``release.cut`` events published for ``product_id``.

    Args:
        events: The captured events.
        product_id: The product the events must be scoped to.

    Yields:
        Each matching ``release.cut`` domain event.
    """
    for event in events:
        if event.event_type == EventType.RELEASE_CUT and event.product_id == product_id:
            yield event


class TestReleaseSse:
    """P2: a cut publishes the ``release.cut`` event the SSE stream fans out (API_CONTRACT §6)."""

    def test_cut_publishes_release_cut_event(self, client: TestClient) -> None:
        """Cutting a release publishes exactly one ``release.cut`` event for the product."""
        # Arrange
        product_id = _seed_released_product(client)
        captured = _capture_published_events(client)

        # Act
        cut = client.post(f"/products/{product_id}/releases", json={"label": "Aurora 5.1"})

        # Assert
        assert cut.status_code == 201, cut.text
        matches = list(_release_cut_events(captured, product_id))
        assert len(matches) == 1, f"exactly one release.cut event must be published; got {matches}"

    def test_release_cut_event_carries_the_release(self, client: TestClient) -> None:
        """The ``release.cut`` payload carries the cut release (``data.release``)."""
        # Arrange
        product_id = _seed_released_product(client)
        captured = _capture_published_events(client)

        # Act
        cut = client.post(f"/products/{product_id}/releases", json={})

        # Assert
        assert cut.status_code == 201, cut.text
        event = next(_release_cut_events(captured, product_id))
        release_payload = event.data.get("release")
        assert release_payload is not None, "release.cut data must carry a 'release' payload (§6)"
        payload_id = (
            release_payload["id"] if isinstance(release_payload, dict) else release_payload.id
        )
        assert str(payload_id) == cut.json()["id"], "the event must carry the cut release"

    def test_no_event_published_without_a_cut(self, client: TestClient) -> None:
        """Seeding versions (but never cutting) publishes no ``release.cut`` event."""
        # Arrange
        product_id = _seed_released_product(client)

        # Act -- start capturing, then perform a non-cut read only.
        captured = _capture_published_events(client)
        client.get(f"/products/{product_id}/releases")

        # Assert
        assert list(_release_cut_events(captured, product_id)) == []

    def test_events_endpoint_streams_text_event_stream(self, client: TestClient) -> None:
        """The SSE endpoint advertises ``text/event-stream`` (the transport for §6 events)."""
        # Arrange
        product_id = _seed_released_product(client)

        # Act -- open the stream and inspect headers only, then close without draining.
        with client.stream("GET", f"/products/{product_id}/events") as stream:
            status = stream.status_code
            content_type = stream.headers.get("content-type", "")

        # Assert
        assert status == 200, f"SSE endpoint must return 200; got {status}"
        assert content_type.startswith("text/event-stream"), (
            f"SSE endpoint must serve text/event-stream; got '{content_type}'"
        )
