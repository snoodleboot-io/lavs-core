"""Integration tests: the version endpoints publish domain events.

These drive the real ``POST /versions`` and rollback routes end to end and
assert the resulting :class:`DomainEvent` on the application's live event bus.
Subscribing to the bus *before* the request keeps the assertion deterministic:
the publish runs in the app event loop during request handling, so the queue
holds the event by the time the HTTP response returns.
"""

from collections.abc import Iterator

import duckdb
import pytest
from fastapi.testclient import TestClient

from app.events.event_bus import EventBus
from app.events.event_type import EventType
from app.models.types.ulid_id import new_ulid


@pytest.fixture()
def client(test_db: str) -> Iterator[TestClient]:
    """Provide a TestClient with the application lifespan active.

    Args:
        test_db: The isolated test database path (from the package conftest).

    Yields:
        A ``TestClient`` whose managed DuckDB connection and event bus are live.
    """
    from app.main import app

    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


def _managed_connection() -> duckdb.DuckDBPyConnection:
    """Return the application's managed DuckDB connection for direct seeding."""
    from app.main import app

    connection: duckdb.DuckDBPyConnection = app.state.db_connection
    return connection


def _event_bus() -> EventBus:
    """Return the application's live event bus."""
    from app.main import app

    bus: EventBus = app.state.event_bus
    return bus


def _seed_component() -> tuple[str, str]:
    """Insert a product + component through the managed connection.

    Returns:
        A ``(component_id, product_id)`` pair for the seeded rows.
    """
    connection = _managed_connection()
    product_id = new_ulid()
    component_id = new_ulid()
    connection.execute("INSERT INTO products (id, name) VALUES (?, ?)", (product_id, "product"))
    connection.execute(
        "INSERT INTO components (id, product_id, name, kind) VALUES (?, ?, ?, ?)",
        (component_id, product_id, "component", "library"),
    )
    return component_id, product_id


def test_create_version_publishes_version_created(client: TestClient) -> None:
    """POST /versions publishes a ``version.created`` for the component's product."""
    # Arrange
    component_id, product_id = _seed_component()
    queue = _event_bus().subscribe(product_id)

    # Act
    response = client.post("/versions", json={"component_id": component_id, "version": "1.2.3"})

    # Assert
    assert response.status_code == 200, response.text
    event = queue.get_nowait()
    assert event.event_type == EventType.VERSION_CREATED
    assert event.product_id == product_id
    assert event.data["component_id"] == component_id
    assert event.data["version"]["id"] == response.json()["id"]
    assert event.data["version"]["status"] == "active"


def test_create_version_event_isolated_to_its_product(client: TestClient) -> None:
    """A subscriber to a different product sees no event from the create."""
    # Arrange
    component_id, _ = _seed_component()
    other_queue = _event_bus().subscribe(new_ulid())

    # Act
    response = client.post("/versions", json={"component_id": component_id, "version": "1.0.0"})

    # Assert
    assert response.status_code == 200, response.text
    assert other_queue.empty()


def test_failed_create_publishes_nothing(client: TestClient) -> None:
    """A 404 create (unknown component) publishes no event."""
    # Arrange
    _, product_id = _seed_component()
    queue = _event_bus().subscribe(product_id)

    # Act
    response = client.post("/versions", json={"component_id": new_ulid(), "version": "1.0.0"})

    # Assert
    assert response.status_code == 404, response.text
    assert queue.empty()


def test_rollback_publishes_version_rolled_back(client: TestClient) -> None:
    """Rollback publishes ``version.rolled_back`` with target and reactivated ids."""
    # Arrange
    component_id, product_id = _seed_component()
    first = client.post("/versions", json={"component_id": component_id, "version": "1.0.0"}).json()
    second = client.post(
        "/versions", json={"component_id": component_id, "version": "2.0.0"}
    ).json()
    queue = _event_bus().subscribe(product_id)

    # Act
    response = client.post(f"/versions/{second['id']}/rollback")

    # Assert
    assert response.status_code == 200, response.text
    event = queue.get_nowait()
    assert event.event_type == EventType.VERSION_ROLLED_BACK
    assert event.product_id == product_id
    assert event.data == {
        "component_id": component_id,
        "version_id": second["id"],
        "reactivated_version_id": first["id"],
    }


def test_failed_rollback_publishes_nothing(client: TestClient) -> None:
    """A 409 rollback (no prior version) publishes no event."""
    # Arrange
    component_id, product_id = _seed_component()
    only = client.post("/versions", json={"component_id": component_id, "version": "1.0.0"}).json()
    queue = _event_bus().subscribe(product_id)

    # Act
    response = client.post(f"/versions/{only['id']}/rollback")

    # Assert
    assert response.status_code == 409, response.text
    assert queue.empty()
