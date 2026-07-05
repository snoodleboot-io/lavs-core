"""Unit tests for :class:`GetProductByIdQuery`."""

from unittest import IsolatedAsyncioTestCase

import duckdb

from app.database.database_manager import DatabaseManager
from app.errors.not_found_error import NotFoundError
from app.models.responses.product_response_model import ProductResponseModel
from app.queries.products.get_product_by_id_query import GetProductByIdQuery
from app.queries.products.product_id_request import ProductIdRequest


class TestGetProductByIdQuery(IsolatedAsyncioTestCase):
    """Behaviour of the fetch-by-id query against an in-memory database."""

    def setUp(self) -> None:
        """Open an in-memory DuckDB and install the real schema."""
        self._conn = duckdb.connect(":memory:")
        DatabaseManager.create_tables_on(self._conn)

    def tearDown(self) -> None:
        """Close the in-memory connection."""
        self._conn.close()

    async def test_returns_matching_product(self) -> None:
        """An existing id yields the corresponding response model."""
        # Arrange
        self._conn.execute(
            "INSERT INTO products (id, name, description) VALUES (?, ?, ?)",
            ["01AAAAAAAAAAAAAAAAAAAAAAAA", "Aurora", "Flagship"],
        )
        request = ProductIdRequest(product_id="01AAAAAAAAAAAAAAAAAAAAAAAA")

        # Act
        result = await GetProductByIdQuery().execute(data=request, connection=self._conn)

        # Assert
        assert isinstance(result, ProductResponseModel)
        assert result.id == "01AAAAAAAAAAAAAAAAAAAAAAAA"
        assert result.name == "Aurora"
        assert result.description == "Flagship"

    async def test_unknown_id_raises_not_found(self) -> None:
        """An id with no matching row raises :class:`NotFoundError`."""
        # Arrange
        request = ProductIdRequest(product_id="01ZZZZZZZZZZZZZZZZZZZZZZZZ")

        # Act / Assert
        with self.assertRaises(NotFoundError) as caught:
            await GetProductByIdQuery().execute(data=request, connection=self._conn)
        assert caught.exception.details == {"id": "01ZZZZZZZZZZZZZZZZZZZZZZZZ"}
