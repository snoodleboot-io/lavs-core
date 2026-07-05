"""Unit tests for :class:`ListComponentsByProductQuery`."""

from unittest import IsolatedAsyncioTestCase

import duckdb

from app.database.database_manager import DatabaseManager
from app.models.enums.component_kind import ComponentKind
from app.queries.products.list_components_by_product_query import (
    ListComponentsByProductQuery,
)
from app.queries.products.product_id_request import ProductIdRequest


class TestListComponentsByProductQuery(IsolatedAsyncioTestCase):
    """Behaviour of the list-components query against an in-memory database."""

    def setUp(self) -> None:
        """Open an in-memory DuckDB, install the schema, and seed a product."""
        self._conn = duckdb.connect(":memory:")
        DatabaseManager.create_tables_on(self._conn)
        self._conn.execute(
            "INSERT INTO products (id, name, description) VALUES (?, ?, ?)",
            ["01AAAAAAAAAAAAAAAAAAAAAAAA", "Aurora", None],
        )

    def tearDown(self) -> None:
        """Close the in-memory connection."""
        self._conn.close()

    async def test_returns_components_for_product(self) -> None:
        """Components of the product are returned with a typed ``kind``."""
        # Arrange
        self._conn.execute(
            "INSERT INTO components (id, product_id, name, kind) VALUES (?, ?, ?, ?)",
            ["01CCCCCCCCCCCCCCCCCCCCCCCC", "01AAAAAAAAAAAAAAAAAAAAAAAA", "api", "service"],
        )
        request = ProductIdRequest(product_id="01AAAAAAAAAAAAAAAAAAAAAAAA")

        # Act
        result = await ListComponentsByProductQuery().execute(data=request, connection=self._conn)

        # Assert
        assert len(result) == 1
        assert result[0].name == "api"
        assert result[0].kind is ComponentKind.SERVICE
        assert result[0].product_id == "01AAAAAAAAAAAAAAAAAAAAAAAA"

    async def test_excludes_other_products_components(self) -> None:
        """Only components of the requested product are returned."""
        # Arrange
        self._conn.execute(
            "INSERT INTO products (id, name, description) VALUES (?, ?, ?)",
            ["01BBBBBBBBBBBBBBBBBBBBBBBB", "Borealis", None],
        )
        self._conn.execute(
            "INSERT INTO components (id, product_id, name, kind) VALUES (?, ?, ?, ?)",
            ["01DDDDDDDDDDDDDDDDDDDDDDDD", "01BBBBBBBBBBBBBBBBBBBBBBBB", "cli", "cli"],
        )
        request = ProductIdRequest(product_id="01AAAAAAAAAAAAAAAAAAAAAAAA")

        # Act
        result = await ListComponentsByProductQuery().execute(data=request, connection=self._conn)

        # Assert
        assert result == []

    async def test_product_without_components_returns_empty(self) -> None:
        """A product with no components yields an empty list."""
        # Arrange
        request = ProductIdRequest(product_id="01AAAAAAAAAAAAAAAAAAAAAAAA")

        # Act
        result = await ListComponentsByProductQuery().execute(data=request, connection=self._conn)

        # Assert
        assert result == []
