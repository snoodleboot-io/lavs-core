"""Unit tests for :class:`ListComponentVersionsQuery`."""

import pathlib
from unittest import IsolatedAsyncioTestCase

import duckdb

from app.errors.not_found_error import NotFoundError
from app.models.types.ulid_id import new_ulid
from app.queries.components.list_component_versions_query import (
    ListComponentVersionsQuery,
)
from app.queries.components.list_component_versions_request import (
    ListComponentVersionsRequest,
)

_DDL_PATH = pathlib.Path(__file__).resolve().parents[4] / "app" / "database" / "duckdb" / "ddl.sql"


def _schema_connection() -> duckdb.DuckDBPyConnection:
    """Open an in-memory DuckDB connection with the LAVS schema applied.

    Returns:
        A fresh in-memory connection carrying the products/components/versions
        tables.
    """
    connection = duckdb.connect(":memory:")
    connection.execute(_DDL_PATH.read_text())
    return connection


def _seed_component(connection: duckdb.DuckDBPyConnection) -> str:
    """Insert a product and component, returning the component id.

    Args:
        connection: The connection to insert into.

    Returns:
        The seeded component identifier.
    """
    product_id = new_ulid()
    component_id = new_ulid()
    connection.execute("INSERT INTO products (id, name) VALUES (?, ?)", [product_id, "lavs"])
    connection.execute(
        "INSERT INTO components (id, product_id, name, kind) VALUES (?, ?, ?, ?)",
        [component_id, product_id, "lavs-api", "service"],
    )
    return component_id


def _seed_version(
    connection: duckdb.DuckDBPyConnection,
    component_id: str,
    major: int,
    minor: int,
    patch: int,
) -> None:
    """Insert a version row directly (no versions endpoint exists in this lane).

    Args:
        connection: The connection to insert into.
        component_id: The owning component.
        major: The semver major.
        minor: The semver minor.
        patch: The semver patch.
    """
    connection.execute(
        "INSERT INTO versions (id, component_id, major, minor, patch, prerelease, status) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        [new_ulid(), component_id, major, minor, patch, None, "active"],
    )


class TestListComponentVersionsQuery(IsolatedAsyncioTestCase):
    """Behavior of the list-component-versions query."""

    async def test_returns_versions_semver_descending(self) -> None:
        """Versions are ordered by ``(major, minor, patch)`` descending."""
        # Arrange
        connection = _schema_connection()
        component_id = _seed_component(connection)
        _seed_version(connection, component_id, 1, 0, 0)
        _seed_version(connection, component_id, 2, 0, 1)
        _seed_version(connection, component_id, 2, 0, 0)
        _seed_version(connection, component_id, 1, 5, 9)
        request = ListComponentVersionsRequest(component_id=component_id)

        # Act
        result = await ListComponentVersionsQuery().execute(data=request, connection=connection)

        # Assert
        triples = [(version.major, version.minor, version.patch) for version in result]
        assert triples == [(2, 0, 1), (2, 0, 0), (1, 5, 9), (1, 0, 0)]

    async def test_known_component_without_versions_returns_empty(self) -> None:
        """A known component with no versions yields an empty list."""
        # Arrange
        connection = _schema_connection()
        component_id = _seed_component(connection)
        request = ListComponentVersionsRequest(component_id=component_id)

        # Act
        result = await ListComponentVersionsQuery().execute(data=request, connection=connection)

        # Assert
        assert result == []

    async def test_unknown_component_raises_not_found(self) -> None:
        """An unknown component raises ``NotFoundError``."""
        # Arrange
        connection = _schema_connection()
        request = ListComponentVersionsRequest(component_id=new_ulid())

        # Act / Assert
        with self.assertRaises(NotFoundError):
            await ListComponentVersionsQuery().execute(data=request, connection=connection)

    async def test_version_fields_are_mapped(self) -> None:
        """Each version row maps onto a fully populated response model."""
        # Arrange
        connection = _schema_connection()
        component_id = _seed_component(connection)
        _seed_version(connection, component_id, 3, 2, 1)
        request = ListComponentVersionsRequest(component_id=component_id)

        # Act
        result = await ListComponentVersionsQuery().execute(data=request, connection=connection)

        # Assert
        version = result[0]
        assert version.component_id == component_id
        assert (version.major, version.minor, version.patch) == (3, 2, 1)
        assert version.prerelease is None
        assert version.status.value == "active"
        assert len(version.id) == 26
        assert version.created_at != ""
