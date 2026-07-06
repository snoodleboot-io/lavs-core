"""Unit tests for :class:`TimelineQuery` against an isolated DuckDB."""

from unittest import IsolatedAsyncioTestCase

import duckdb

from app.queries.timeline.timeline_query import TimelineQuery
from app.queries.timeline.timeline_request_model import TimelineRequestModel

_DDL = """
CREATE TABLE products (
    id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    description VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE components (
    id VARCHAR PRIMARY KEY,
    product_id VARCHAR NOT NULL REFERENCES products(id),
    name VARCHAR NOT NULL,
    kind VARCHAR NOT NULL CHECK (kind IN ('library', 'service', 'ui', 'cli'))
);
CREATE TABLE versions (
    id VARCHAR PRIMARY KEY,
    component_id VARCHAR NOT NULL REFERENCES components(id),
    major INTEGER NOT NULL,
    minor INTEGER NOT NULL,
    patch INTEGER NOT NULL,
    prerelease VARCHAR,
    status VARCHAR DEFAULT 'active' CHECK (status IN ('active', 'superseded', 'rolled_back')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def _fresh_connection() -> duckdb.DuckDBPyConnection:
    """Open an in-memory DuckDB with the core relational schema.

    Returns:
        A connection whose ``products``/``components``/``versions`` tables exist.
    """
    conn = duckdb.connect(":memory:")
    conn.execute(_DDL)
    return conn


def _seed_product(conn: duckdb.DuckDBPyConnection, product_id: str, name: str) -> None:
    """Insert a single product row."""
    conn.execute(
        "INSERT INTO products (id, name, description) VALUES (?, ?, ?)",
        (product_id, name, None),
    )


def _seed_component(
    conn: duckdb.DuckDBPyConnection, component_id: str, product_id: str, name: str, kind: str
) -> None:
    """Insert a single component row."""
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
    """Insert a single active version row."""
    conn.execute(
        "INSERT INTO versions (id, component_id, major, minor, patch, prerelease, status) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (version_id, component_id, major, minor, patch, None, "active"),
    )


class TestTimelineQuery(IsolatedAsyncioTestCase):
    """Behaviour of the composite timeline read query."""

    async def test_nests_components_with_versions_ordered_descending(self) -> None:
        """Versions attach to their component, semver descending; empty stays empty."""
        # Arrange
        conn = _fresh_connection()
        _seed_product(conn, "prod-1", "Aurora Platform")
        _seed_component(conn, "comp-a", "prod-1", "lavs-api", "service")
        _seed_component(conn, "comp-b", "prod-1", "lavs-ui", "ui")
        # Insert out of order so ordering is the query's responsibility.
        _seed_version(conn, "v-a-1", "comp-a", 1, 0, 0)
        _seed_version(conn, "v-a-3", "comp-a", 2, 4, 0)
        _seed_version(conn, "v-a-2", "comp-a", 2, 0, 5)
        # comp-b intentionally has no versions.

        # Act
        result = await TimelineQuery().apply(TimelineRequestModel(product_id="prod-1"), conn)

        # Assert
        assert result is not None
        assert result.product.id == "prod-1"
        assert result.product.name == "Aurora Platform"
        assert [component.id for component in result.components] == ["comp-a", "comp-b"]
        comp_a = result.components[0]
        assert [(v.major, v.minor, v.patch) for v in comp_a.versions] == [
            (2, 4, 0),
            (2, 0, 5),
            (1, 0, 0),
        ]
        comp_b = result.components[1]
        assert comp_b.versions == []

    async def test_product_with_no_components_yields_empty_list(self) -> None:
        """A product without components returns an empty ``components`` list."""
        # Arrange
        conn = _fresh_connection()
        _seed_product(conn, "prod-empty", "Lonely Product")

        # Act
        result = await TimelineQuery().apply(TimelineRequestModel(product_id="prod-empty"), conn)

        # Assert
        assert result is not None
        assert result.product.id == "prod-empty"
        assert result.components == []

    async def test_unknown_product_returns_none(self) -> None:
        """An unknown product id resolves to ``None`` (router maps to 404)."""
        # Arrange
        conn = _fresh_connection()

        # Act
        result = await TimelineQuery().apply(TimelineRequestModel(product_id="missing"), conn)

        # Assert
        assert result is None

    async def test_versions_are_scoped_to_the_requested_product(self) -> None:
        """Versions of another product's component never leak into the timeline."""
        # Arrange
        conn = _fresh_connection()
        _seed_product(conn, "prod-1", "Aurora")
        _seed_product(conn, "prod-2", "Borealis")
        _seed_component(conn, "comp-1", "prod-1", "api", "service")
        _seed_component(conn, "comp-2", "prod-2", "api", "service")
        _seed_version(conn, "v-1", "comp-1", 1, 0, 0)
        _seed_version(conn, "v-2", "comp-2", 9, 9, 9)

        # Act
        result = await TimelineQuery().apply(TimelineRequestModel(product_id="prod-1"), conn)

        # Assert
        assert result is not None
        assert [component.id for component in result.components] == ["comp-1"]
        assert [v.id for v in result.components[0].versions] == ["v-1"]
