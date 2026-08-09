"""Integration tests for ``POST /products/{id}/releases`` end to end.

These exercise the real router, cut query, event bus, and error-envelope wiring
against a live app + DuckDB. The module-local ``client`` fixture runs the
application ``lifespan`` so the managed connection and event bus exist;
components and versions are seeded directly through that managed connection,
since this lane adds no create endpoints.
"""

from collections.abc import Iterator

import duckdb
import pytest
from fastapi.testclient import TestClient

from app.events.domain_event import DomainEvent
from app.events.event_bus import EventBus
from app.models.enums.version_status import VersionStatus
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
    """Return the application's managed event bus."""
    from app.main import app

    event_bus: EventBus = app.state.event_bus
    return event_bus


def _seed_product(base_version: str = "0.0.0") -> str:
    """Insert a product through the managed connection and return its id."""
    connection = _managed_connection()
    product_id = new_ulid()
    connection.execute(
        "INSERT INTO products (id, name, base_version) VALUES (?, ?, ?)",
        (product_id, "product", base_version),
    )
    return product_id


def _seed_component(product_id: str, name: str) -> str:
    """Insert a component under ``product_id`` and return its id."""
    connection = _managed_connection()
    component_id = new_ulid()
    connection.execute(
        "INSERT INTO components (id, product_id, name, kind) VALUES (?, ?, ?, ?)",
        (component_id, product_id, name, "library"),
    )
    return component_id


def _seed_active_version(component_id: str, major: int, minor: int, patch: int) -> str:
    """Insert an active version for ``component_id`` and return its id."""
    connection = _managed_connection()
    version_id = new_ulid()
    connection.execute(
        "INSERT INTO versions "
        "(id, component_id, major, minor, patch, prerelease, status) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (version_id, component_id, major, minor, patch, None, VersionStatus.ACTIVE.value),
    )
    return version_id


def test_cut_release_returns_201_with_frozen_manifest(client: TestClient) -> None:
    """POST cut returns 201 with the derived version and pinned manifest."""
    # Arrange
    product_id = _seed_product(base_version="0.0.0")
    api = _seed_component(product_id, "api")
    ui = _seed_component(product_id, "ui")
    api_version = _seed_active_version(api, 2, 4, 0)
    ui_version = _seed_active_version(ui, 1, 0, 0)

    # Act
    response = client.post(f"/products/{product_id}/releases", json={"label": "Aurora"})

    # Assert
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["product_id"] == product_id
    assert body["product_version"] == "0.1.0"
    assert body["label"] == "Aurora"
    pinned = {component["component_id"]: component for component in body["components"]}
    assert pinned[api]["version_id"] == api_version
    assert pinned[api]["version"] == "2.4.0"
    assert pinned[ui]["version_id"] == ui_version


def test_cut_release_publishes_release_cut_event(client: TestClient) -> None:
    """A fresh cut publishes a ``release.cut`` event for the product."""
    # Arrange
    product_id = _seed_product()
    component_id = _seed_component(product_id, "api")
    _seed_active_version(component_id, 1, 0, 0)
    queue = _event_bus().subscribe(product_id)

    # Act
    response = client.post(f"/products/{product_id}/releases", json={})

    # Assert
    assert response.status_code == 201, response.text
    assert not queue.empty()
    event: DomainEvent = queue.get_nowait()
    assert event.event_type.value == "release.cut"
    assert event.product_id == product_id
    assert event.data["release"]["id"] == response.json()["id"]


def test_cut_release_unknown_product_returns_404(client: TestClient) -> None:
    """Cutting under an unknown product yields a 404 envelope."""
    # Arrange
    unknown_product = new_ulid()

    # Act
    response = client.post(f"/products/{unknown_product}/releases", json={})

    # Assert
    assert response.status_code == 404, response.text
    assert response.json()["error"]["code"] == "not_found"


def test_cut_release_nothing_active_returns_409(client: TestClient) -> None:
    """A product with no active version yields a 409 envelope."""
    # Arrange
    product_id = _seed_product()
    _seed_component(product_id, "api")

    # Act
    response = client.post(f"/products/{product_id}/releases", json={})

    # Assert
    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "conflict"


def test_cut_release_idempotency_key_dedupes(client: TestClient) -> None:
    """Two POSTs with the same Idempotency-Key yield one release, no double bump."""
    # Arrange
    product_id = _seed_product()
    component_id = _seed_component(product_id, "api")
    _seed_active_version(component_id, 1, 0, 0)
    headers = {"Idempotency-Key": "cut-once"}

    # Act
    first = client.post(f"/products/{product_id}/releases", json={}, headers=headers)
    second = client.post(f"/products/{product_id}/releases", json={}, headers=headers)

    # Assert
    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    assert second.json()["id"] == first.json()["id"]
    assert second.json()["product_version"] == first.json()["product_version"]
    release_count = (
        _managed_connection()
        .execute("SELECT count(*) FROM releases WHERE product_id = ?", (product_id,))
        .fetchone()
    )
    assert release_count is not None
    assert release_count[0] == 1
