"""Unit tests for :class:`ListProductsQuery`."""

from unittest import IsolatedAsyncioTestCase

import duckdb

from app.database.database_manager import DatabaseManager
from app.models.requests.request_model import RequestModel
from app.queries.products.list_products_query import ListProductsQuery


class TestListProductsQuery(IsolatedAsyncioTestCase):
    """Behaviour of the list-all query against an in-memory database."""

    def setUp(self) -> None:
        """Open an in-memory DuckDB and install the real schema."""
        self._conn = duckdb.connect(":memory:")
        DatabaseManager.create_tables_on(self._conn)

    def tearDown(self) -> None:
        """Close the in-memory connection."""
        self._conn.close()

    async def test_returns_empty_list_when_no_products(self) -> None:
        """No products yields an empty list."""
        # Act
        result = await ListProductsQuery().execute(data=RequestModel(), connection=self._conn)

        # Assert
        assert result == []

    async def test_returns_all_products(self) -> None:
        """Every stored product is returned as a response model."""
        # Arrange
        self._conn.execute(
            "INSERT INTO products (id, name, description) VALUES (?, ?, ?)",
            ["01AAAAAAAAAAAAAAAAAAAAAAAA", "Aurora", None],
        )
        self._conn.execute(
            "INSERT INTO products (id, name, description) VALUES (?, ?, ?)",
            ["01BBBBBBBBBBBBBBBBBBBBBBBB", "Borealis", "Second"],
        )

        # Act
        result = await ListProductsQuery().execute(data=RequestModel(), connection=self._conn)

        # Assert
        assert len(result) == 2
        names = {product.name for product in result}
        assert names == {"Aurora", "Borealis"}
