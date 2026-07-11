"""Integration tests for the release-read routes.

Covers ``GET /products/{product_id}/releases`` (ledger) and
``GET /releases/{release_id}`` (frozen manifest). The tests enter the
``TestClient`` as a context manager so the application lifespan runs and the
managed DuckDB connection is available; every row is seeded directly through
that connection via parameterized SQL — the cut endpoint (R1's) is never called.
"""

import duckdb
from fastapi.testclient import TestClient


def _connection(client: TestClient) -> duckdb.DuckDBPyConnection:
    """Return the live managed DuckDB connection behind the client."""
    connection: duckdb.DuckDBPyConnection = client.app.state.db_connection
    return connection


def _seed_product(conn: duckdb.DuckDBPyConnection, product_id: str) -> None:
    """Insert a product row via parameterized SQL."""
    conn.execute(
        "INSERT INTO products (id, name, description) VALUES (?, ?, ?)",
        (product_id, "Aurora Platform", None),
    )


def _seed_component(conn: duckdb.DuckDBPyConnection, component_id: str, name: str) -> None:
    """Insert a component row via parameterized SQL."""
    conn.execute(
        "INSERT INTO components (id, product_id, name, kind) VALUES (?, ?, ?, ?)",
        (component_id, "prod-1", name, "service"),
    )


def _seed_version(
    conn: duckdb.DuckDBPyConnection,
    version_id: str,
    component_id: str,
    major: int,
    minor: int,
    patch: int,
    prerelease: str | None = None,
) -> None:
    """Insert a version row via parameterized SQL."""
    conn.execute(
        "INSERT INTO versions (id, component_id, major, minor, patch, prerelease, status) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (version_id, component_id, major, minor, patch, prerelease, "active"),
    )


def _seed_release(
    conn: duckdb.DuckDBPyConnection,
    release_id: str,
    product_version: str,
    created_at: str,
    label: str | None = None,
) -> None:
    """Insert a release row via parameterized SQL."""
    conn.execute(
        "INSERT INTO releases (id, product_id, product_version, label, notes, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (release_id, "prod-1", product_version, label, None, created_at),
    )


def _pin(
    conn: duckdb.DuckDBPyConnection, release_id: str, component_id: str, version_id: str
) -> None:
    """Pin a component version into a release manifest via parameterized SQL."""
    conn.execute(
        "INSERT INTO release_components (release_id, component_id, version_id) VALUES (?, ?, ?)",
        (release_id, component_id, version_id),
    )


class TestListProductReleasesEndpoint:
    """End-to-end behaviour of ``GET /products/{product_id}/releases``."""

    def test_returns_ledger_newest_first_with_manifests(self, client: TestClient) -> None:
        """The ledger is newest-first and each release carries its manifest."""
        # Arrange
        with client as active:
            conn = _connection(active)
            _seed_product(conn, "prod-1")
            _seed_component(conn, "comp-a", "lavs-api")
            _seed_version(conn, "v-a-1", "comp-a", 2, 4, 0)
            _seed_release(conn, "rel-old", "5.1.0", "2026-06-29T12:00:00", label="Aurora 5.1")
            _seed_release(conn, "rel-new", "5.2.0", "2026-06-30T12:00:00")
            _pin(conn, "rel-old", "comp-a", "v-a-1")
            _pin(conn, "rel-new", "comp-a", "v-a-1")

            # Act
            response = active.get("/products/prod-1/releases")

        # Assert
        assert response.status_code == 200, response.text
        body = response.json()
        assert [release["id"] for release in body] == ["rel-new", "rel-old"]
        old = next(release for release in body if release["id"] == "rel-old")
        assert old["product_version"] == "5.1.0"
        assert old["label"] == "Aurora 5.1"
        assert old["components"][0]["name"] == "lavs-api"
        assert old["components"][0]["version"] == "2.4.0"
        assert old["components"][0]["version_id"] == "v-a-1"

    def test_known_product_without_releases_returns_empty_list(self, client: TestClient) -> None:
        """A product with no releases returns an empty ledger."""
        # Arrange
        with client as active:
            conn = _connection(active)
            _seed_product(conn, "prod-1")

            # Act
            response = active.get("/products/prod-1/releases")

        # Assert
        assert response.status_code == 200, response.text
        assert response.json() == []

    def test_unknown_product_returns_404_envelope(self, client: TestClient) -> None:
        """An unknown product yields a 404 with the ``not_found`` envelope."""
        # Arrange
        with client as active:
            # Act
            response = active.get("/products/does-not-exist/releases")

        # Assert
        assert response.status_code == 404, response.text
        body = response.json()
        assert body["error"]["code"] == "not_found"
        assert body["error"]["details"]["product_id"] == "does-not-exist"


class TestGetReleaseEndpoint:
    """End-to-end behaviour of ``GET /releases/{release_id}``."""

    def test_returns_single_release_with_manifest(self, client: TestClient) -> None:
        """A known release comes back with its frozen manifest."""
        # Arrange
        with client as active:
            conn = _connection(active)
            _seed_product(conn, "prod-1")
            _seed_component(conn, "comp-a", "lavs-api")
            _seed_version(conn, "v-a-1", "comp-a", 0, 9, 0, prerelease="rc.1")
            _seed_release(conn, "rel-a", "5.1.0", "2026-06-29T12:00:00")
            _pin(conn, "rel-a", "comp-a", "v-a-1")

            # Act
            response = active.get("/releases/rel-a")

        # Assert
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["id"] == "rel-a"
        assert body["product_id"] == "prod-1"
        assert body["product_version"] == "5.1.0"
        assert len(body["components"]) == 1
        assert body["components"][0]["version"] == "0.9.0-rc.1"

    def test_unknown_release_returns_404_envelope(self, client: TestClient) -> None:
        """An unknown release id yields a 404 with the ``not_found`` envelope."""
        # Arrange
        with client as active:
            # Act
            response = active.get("/releases/does-not-exist")

        # Assert
        assert response.status_code == 404, response.text
        body = response.json()
        assert body["error"]["code"] == "not_found"
        assert body["error"]["details"]["release_id"] == "does-not-exist"
