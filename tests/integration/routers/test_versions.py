"""Integration tests for the ``/versions`` routes against a live app + DuckDB.

These exercise the real router, query, and error-envelope wiring end to end.
The module-local ``client`` fixture overrides the package fixture so the
application ``lifespan`` runs (opening the managed DuckDB connection the query
layer depends on). Components are seeded directly through that same managed
connection, since no component-create endpoint exists in this lane.
"""

from collections.abc import Iterator

import duckdb
import pytest
from fastapi.testclient import TestClient

from app.models.types.ulid_id import new_ulid


@pytest.fixture()
def client(test_db: str) -> Iterator[TestClient]:
    """Provide a TestClient with the application lifespan active.

    Args:
        test_db: The isolated test database path (from the package conftest).

    Yields:
        A ``TestClient`` whose managed DuckDB connection is open.
    """
    from app.main import app

    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


def _managed_connection() -> duckdb.DuckDBPyConnection:
    """Return the application's managed DuckDB connection for direct seeding."""
    from app.main import app

    connection: duckdb.DuckDBPyConnection = app.state.db_connection
    return connection


def _seed_component() -> str:
    """Insert a product + component through the managed connection.

    Returns:
        The id of the seeded component.
    """
    connection = _managed_connection()
    product_id = new_ulid()
    component_id = new_ulid()
    connection.execute("INSERT INTO products (id, name) VALUES (?, ?)", (product_id, "product"))
    connection.execute(
        "INSERT INTO components (id, product_id, name, kind) VALUES (?, ?, ?, ?)",
        (component_id, product_id, "component", "library"),
    )
    return component_id


def test_create_version_returns_active(client: TestClient) -> None:
    """POST /versions creates an active version (200)."""
    # Arrange
    component_id = _seed_component()

    # Act
    response = client.post("/versions", json={"component_id": component_id, "version": "1.0.0"})

    # Assert
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "active"
    assert body["component_id"] == component_id
    assert (body["major"], body["minor"], body["patch"]) == (1, 0, 0)


def test_second_create_supersedes_prior(client: TestClient) -> None:
    """A second create supersedes the first and keeps both rows."""
    # Arrange
    component_id = _seed_component()
    first = client.post("/versions", json={"component_id": component_id, "version": "1.0.0"}).json()

    # Act
    second = client.post("/versions", json={"component_id": component_id, "version": "2.0.0"})

    # Assert
    assert second.status_code == 200, second.text
    assert second.json()["status"] == "active"
    connection = _managed_connection()
    first_status = connection.execute(
        "SELECT status FROM versions WHERE id = ?", (first["id"],)
    ).fetchone()
    assert first_status is not None
    assert first_status[0] == "superseded"


def test_create_under_unknown_component_returns_404(client: TestClient) -> None:
    """Creating under an unknown component yields a 404 envelope."""
    # Arrange
    unknown_component = new_ulid()

    # Act
    response = client.post(
        "/versions", json={"component_id": unknown_component, "version": "1.0.0"}
    )

    # Assert
    assert response.status_code == 404, response.text
    assert response.json()["error"]["code"] == "not_found"


def test_create_with_non_semver_returns_422(client: TestClient) -> None:
    """A non-semantic version string is rejected with 422."""
    # Arrange
    component_id = _seed_component()

    # Act
    response = client.post(
        "/versions", json={"component_id": component_id, "version": "not-a-semver"}
    )

    # Assert
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "validation_error"


def test_rollback_reactivates_previous_without_deleting(client: TestClient) -> None:
    """Rollback flips status, re-activates the prior version, and deletes nothing."""
    # Arrange
    component_id = _seed_component()
    first = client.post("/versions", json={"component_id": component_id, "version": "1.0.0"}).json()
    second = client.post(
        "/versions", json={"component_id": component_id, "version": "2.0.0"}
    ).json()
    connection = _managed_connection()
    before = connection.execute("SELECT count(*) FROM versions").fetchone()
    assert before is not None

    # Act
    response = client.post(f"/versions/{second['id']}/rollback")

    # Assert
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == first["id"]
    assert body["status"] == "active"
    after = connection.execute("SELECT count(*) FROM versions").fetchone()
    assert after is not None
    assert after[0] == before[0]
    rolled_back = connection.execute(
        "SELECT status FROM versions WHERE id = ?", (second["id"],)
    ).fetchone()
    assert rolled_back is not None
    assert rolled_back[0] == "rolled_back"


def test_rollback_with_no_prior_returns_409(client: TestClient) -> None:
    """Rolling back the only version yields a 409 envelope."""
    # Arrange
    component_id = _seed_component()
    only = client.post("/versions", json={"component_id": component_id, "version": "1.0.0"}).json()

    # Act
    response = client.post(f"/versions/{only['id']}/rollback")

    # Assert
    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "conflict"


def test_rollback_unknown_version_returns_404(client: TestClient) -> None:
    """Rolling back an unknown version id yields a 404 envelope."""
    # Arrange
    unknown_version = new_ulid()

    # Act
    response = client.post(f"/versions/{unknown_version}/rollback")

    # Assert
    assert response.status_code == 404, response.text
    assert response.json()["error"]["code"] == "not_found"
