"""Integration tests for the ``/components`` router.

These exercise the real application wiring (router, models, query layer) against
an isolated, lifespan-managed DuckDB. Product and version rows are seeded through
the application's own managed connection because those write paths belong to
other resource lanes.
"""

import os
import pathlib
import shutil
import tempfile
import uuid
from collections.abc import Iterator

import duckdb
import pytest
from fastapi.testclient import TestClient

from app.models.types.ulid_id import new_ulid

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
_DDL_PATH = _REPO_ROOT / "app" / "database" / "duckdb" / "ddl.sql"


@pytest.fixture(scope="function")
def app_client() -> Iterator[TestClient]:
    """Provide a lifespan-managed ``TestClient`` bound to an isolated database.

    Yields:
        A ``TestClient`` whose application lifespan has opened the managed
        DuckDB connection used by the query layer.
    """
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, f"itest_{uuid.uuid4().hex[:8]}.db")

    seed_connection = duckdb.connect(db_path)
    seed_connection.execute(_DDL_PATH.read_text())
    seed_connection.close()

    import app.configurations.configuration as config_module

    original_get_database_path = config_module.get_database_path
    original_get_duckdb_database_name = config_module.get_duckdb_database_name
    config_module.get_database_path = lambda: db_path
    config_module.get_duckdb_database_name = lambda: db_path
    config_module.load_database_config.cache_clear()

    try:
        from app.main import app

        with TestClient(app, raise_server_exceptions=False) as test_client:
            yield test_client
    finally:
        config_module.get_database_path = original_get_database_path
        config_module.get_duckdb_database_name = original_get_duckdb_database_name
        config_module.load_database_config.cache_clear()
        shutil.rmtree(temp_dir, ignore_errors=True)


def _managed_connection(client: TestClient) -> duckdb.DuckDBPyConnection:
    """Return the application's live managed DuckDB connection.

    Args:
        client: The lifespan-managed test client.

    Returns:
        The DuckDB connection opened by the application lifespan.
    """
    connection: duckdb.DuckDBPyConnection = client.app.state.db_connection
    return connection


def _seed_product(client: TestClient) -> str:
    """Insert a product row through the managed connection.

    Args:
        client: The lifespan-managed test client.

    Returns:
        The seeded product identifier.
    """
    product_id = new_ulid()
    _managed_connection(client).execute(
        "INSERT INTO products (id, name) VALUES (?, ?)", [product_id, "lavs"]
    )
    return product_id


def _seed_component(client: TestClient, product_id: str) -> str:
    """Insert a component row through the managed connection.

    Args:
        client: The lifespan-managed test client.
        product_id: The owning product.

    Returns:
        The seeded component identifier.
    """
    component_id = new_ulid()
    _managed_connection(client).execute(
        "INSERT INTO components (id, product_id, name, kind) VALUES (?, ?, ?, ?)",
        [component_id, product_id, "lavs-api", "service"],
    )
    return component_id


def _seed_version(
    client: TestClient, component_id: str, major: int, minor: int, patch: int
) -> None:
    """Insert a version row directly (the versions endpoint lives elsewhere).

    Args:
        client: The lifespan-managed test client.
        component_id: The owning component.
        major: The semver major.
        minor: The semver minor.
        patch: The semver patch.
    """
    _managed_connection(client).execute(
        "INSERT INTO versions (id, component_id, major, minor, patch, prerelease, status) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        [new_ulid(), component_id, major, minor, patch, None, "active"],
    )


def test_create_component_returns_created(app_client: TestClient) -> None:
    """POST /components creates a component for an existing product."""
    # Arrange
    product_id = _seed_product(app_client)

    # Act
    response = app_client.post(
        "/components",
        json={"product_id": product_id, "name": "lavs-api", "kind": "service"},
    )

    # Assert
    assert response.status_code == 201
    body = response.json()
    assert body["product_id"] == product_id
    assert body["name"] == "lavs-api"
    assert body["kind"] == "service"
    assert len(body["id"]) == 26


def test_create_component_unknown_product_returns_404(app_client: TestClient) -> None:
    """POST /components against a missing product returns a 404 envelope."""
    # Act
    response = app_client.post(
        "/components",
        json={"product_id": new_ulid(), "name": "orphan", "kind": "library"},
    )

    # Assert
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_create_component_invalid_kind_returns_422(app_client: TestClient) -> None:
    """POST /components with an unknown kind fails request validation."""
    # Arrange
    product_id = _seed_product(app_client)

    # Act
    response = app_client.post(
        "/components",
        json={"product_id": product_id, "name": "x", "kind": "firmware"},
    )

    # Assert
    assert response.status_code == 422


def test_create_component_invalid_product_id_returns_422(app_client: TestClient) -> None:
    """POST /components with a non-ULID product_id fails request validation."""
    # Act
    response = app_client.post(
        "/components",
        json={"product_id": "not-a-ulid", "name": "x", "kind": "cli"},
    )

    # Assert
    assert response.status_code == 422


def test_list_versions_returns_semver_descending(app_client: TestClient) -> None:
    """GET /components/{id}/versions returns versions newest-semver first."""
    # Arrange
    product_id = _seed_product(app_client)
    component_id = _seed_component(app_client, product_id)
    _seed_version(app_client, component_id, 1, 0, 0)
    _seed_version(app_client, component_id, 2, 0, 1)
    _seed_version(app_client, component_id, 2, 0, 0)

    # Act
    response = app_client.get(f"/components/{component_id}/versions")

    # Assert
    assert response.status_code == 200
    triples = [(v["major"], v["minor"], v["patch"]) for v in response.json()]
    assert triples == [(2, 0, 1), (2, 0, 0), (1, 0, 0)]


def test_list_versions_known_component_without_versions_is_empty(
    app_client: TestClient,
) -> None:
    """GET versions for a known component with no versions returns an empty list."""
    # Arrange
    product_id = _seed_product(app_client)
    component_id = _seed_component(app_client, product_id)

    # Act
    response = app_client.get(f"/components/{component_id}/versions")

    # Assert
    assert response.status_code == 200
    assert response.json() == []


def test_list_versions_unknown_component_returns_404(app_client: TestClient) -> None:
    """GET versions for an unknown component returns a 404 envelope."""
    # Act
    response = app_client.get(f"/components/{new_ulid()}/versions")

    # Assert
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
