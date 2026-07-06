"""Integration tests for ``GET /products/{product_id}/timeline``.

The tests enter the ``TestClient`` as a context manager so the application
lifespan runs and the managed DuckDB connection is available; rows are seeded
directly through that connection via parameterized SQL (no other lane's
endpoints are called).
"""

import duckdb
from fastapi.testclient import TestClient


def _connection(client: TestClient) -> duckdb.DuckDBPyConnection:
    """Return the live managed DuckDB connection behind the client."""
    connection: duckdb.DuckDBPyConnection = client.app.state.db_connection
    return connection


def _seed_product(conn: duckdb.DuckDBPyConnection, product_id: str, name: str) -> None:
    """Insert a product row via parameterized SQL."""
    conn.execute(
        "INSERT INTO products (id, name, description) VALUES (?, ?, ?)",
        (product_id, name, None),
    )


def _seed_component(
    conn: duckdb.DuckDBPyConnection, component_id: str, product_id: str, name: str, kind: str
) -> None:
    """Insert a component row via parameterized SQL."""
    conn.execute(
        "INSERT INTO components (id, product_id, name, kind) VALUES (?, ?, ?, ?)",
        (component_id, product_id, name, kind),
    )


def _seed_version(
    conn: duckdb.DuckDBPyConnection,
    version_id: str,
    component_id: str,
    major: int,
    minor: int,
    patch: int,
) -> None:
    """Insert an active version row via parameterized SQL."""
    conn.execute(
        "INSERT INTO versions (id, component_id, major, minor, patch, prerelease, status) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (version_id, component_id, major, minor, patch, None, "active"),
    )


class TestTimelineEndpoint:
    """End-to-end behaviour of the timeline composite endpoint."""

    def test_happy_path_returns_nested_shape_ordered_descending(self, client: TestClient) -> None:
        """The nested product/component/version shape comes back correctly ordered."""
        # Arrange
        with client as active:
            conn = _connection(active)
            _seed_product(conn, "prod-1", "Aurora Platform")
            _seed_component(conn, "comp-a", "prod-1", "lavs-api", "service")
            _seed_component(conn, "comp-b", "prod-1", "lavs-ui", "ui")
            _seed_version(conn, "v-a-1", "comp-a", 1, 0, 0)
            _seed_version(conn, "v-a-3", "comp-a", 2, 4, 0)
            _seed_version(conn, "v-a-2", "comp-a", 2, 0, 5)
            _seed_version(conn, "v-b-1", "comp-b", 0, 9, 0)

            # Act
            response = active.get("/products/prod-1/timeline")

        # Assert
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["product"]["id"] == "prod-1"
        assert body["product"]["name"] == "Aurora Platform"
        assert [c["id"] for c in body["components"]] == ["comp-a", "comp-b"]
        comp_a = body["components"][0]
        assert [[v["major"], v["minor"], v["patch"]] for v in comp_a["versions"]] == [
            [2, 4, 0],
            [2, 0, 5],
            [1, 0, 0],
        ]
        assert comp_a["kind"] == "service"

    def test_unknown_product_returns_404_envelope(self, client: TestClient) -> None:
        """An unknown product id yields a 404 with the ``not_found`` envelope."""
        # Arrange
        with client as active:
            # Act
            response = active.get("/products/does-not-exist/timeline")

        # Assert
        assert response.status_code == 404, response.text
        body = response.json()
        assert body["error"]["code"] == "not_found"
        assert body["error"]["details"]["product_id"] == "does-not-exist"

    def test_product_with_no_components_returns_empty_list(self, client: TestClient) -> None:
        """A product with no components returns ``components: []``."""
        # Arrange
        with client as active:
            conn = _connection(active)
            _seed_product(conn, "prod-empty", "Lonely Product")

            # Act
            response = active.get("/products/prod-empty/timeline")

        # Assert
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["components"] == []

    def test_component_with_no_versions_returns_empty_versions(self, client: TestClient) -> None:
        """A component without versions returns ``versions: []``."""
        # Arrange
        with client as active:
            conn = _connection(active)
            _seed_product(conn, "prod-1", "Aurora Platform")
            _seed_component(conn, "comp-a", "prod-1", "lavs-api", "service")

            # Act
            response = active.get("/products/prod-1/timeline")

        # Assert
        assert response.status_code == 200, response.text
        body = response.json()
        assert len(body["components"]) == 1
        assert body["components"][0]["versions"] == []
