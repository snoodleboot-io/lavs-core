"""Unit tests for :class:`CreateComponentQuery`."""

import pathlib
from unittest import IsolatedAsyncioTestCase

import duckdb

from app.errors.not_found_error import NotFoundError
from app.models.enums.component_kind import ComponentKind
from app.models.requests.create_component_model import CreateComponentModel
from app.models.types.ulid_id import new_ulid
from app.queries.components.create_component_query import CreateComponentQuery

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


def _seed_product(connection: duckdb.DuckDBPyConnection, product_id: str) -> None:
    """Insert a minimal product row.

    Args:
        connection: The connection to insert into.
        product_id: The product identifier to seed.
    """
    connection.execute(
        "INSERT INTO products (id, name) VALUES (?, ?)",
        [product_id, "lavs"],
    )


class TestCreateComponentQuery(IsolatedAsyncioTestCase):
    """Behavior of the create-component query."""

    async def test_creates_component_for_existing_product(self) -> None:
        """A component is minted and persisted for an existing product."""
        # Arrange
        connection = _schema_connection()
        product_id = new_ulid()
        _seed_product(connection, product_id)
        data = CreateComponentModel(
            product_id=product_id, name="lavs-api", kind=ComponentKind.SERVICE
        )

        # Act
        result = await CreateComponentQuery().execute(data=data, connection=connection)

        # Assert
        assert result.product_id == product_id
        assert result.name == "lavs-api"
        assert result.kind is ComponentKind.SERVICE
        assert len(result.id) == 26
        persisted = connection.execute(
            "SELECT product_id, name, kind FROM components WHERE id = ?", [result.id]
        ).fetchone()
        assert persisted == (product_id, "lavs-api", "service")

    async def test_unknown_product_raises_not_found(self) -> None:
        """Creating against a missing product raises ``NotFoundError``."""
        # Arrange
        connection = _schema_connection()
        data = CreateComponentModel(
            product_id=new_ulid(), name="orphan", kind=ComponentKind.LIBRARY
        )

        # Act / Assert
        with self.assertRaises(NotFoundError):
            await CreateComponentQuery().execute(data=data, connection=connection)

    async def test_duplicate_name_within_product_is_allowed(self) -> None:
        """Two components may share a name under one product with distinct ids."""
        # Arrange
        connection = _schema_connection()
        product_id = new_ulid()
        _seed_product(connection, product_id)
        data = CreateComponentModel(product_id=product_id, name="shared", kind=ComponentKind.CLI)

        # Act
        first = await CreateComponentQuery().execute(data=data, connection=connection)
        second = await CreateComponentQuery().execute(data=data, connection=connection)

        # Assert
        assert first.id != second.id
        count = connection.execute(
            "SELECT COUNT(*) FROM components WHERE product_id = ? AND name = ?",
            [product_id, "shared"],
        ).fetchone()
        assert count == (2,)
