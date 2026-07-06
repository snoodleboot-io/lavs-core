"""Unit tests for :class:`CreateProductQuery`."""

from unittest import IsolatedAsyncioTestCase

import duckdb

from app.database.database_manager import DatabaseManager
from app.errors.conflict_error import ConflictError
from app.models.requests.create_product_model import CreateProductModel
from app.models.responses.product_response_model import ProductResponseModel
from app.models.types.ulid_id import validate_ulid
from app.queries.products.create_product_query import CreateProductQuery


class TestCreateProductQuery(IsolatedAsyncioTestCase):
    """Behaviour of the product-creation query against an in-memory database."""

    def setUp(self) -> None:
        """Open an in-memory DuckDB and install the real schema."""
        self._conn = duckdb.connect(":memory:")
        DatabaseManager.create_tables_on(self._conn)

    def tearDown(self) -> None:
        """Close the in-memory connection."""
        self._conn.close()

    async def test_creates_product_with_minted_ulid(self) -> None:
        """A created product carries a valid ULID id and echoes its fields."""
        # Arrange
        data = CreateProductModel(name="Aurora", description="Flagship")

        # Act
        result = await CreateProductQuery().execute(data=data, connection=self._conn)

        # Assert
        assert isinstance(result, ProductResponseModel)
        assert validate_ulid(result.id) == result.id
        assert result.name == "Aurora"
        assert result.description == "Flagship"
        assert result.created_at != ""

    async def test_persists_row_readable_after_creation(self) -> None:
        """The created product is retrievable in the products table."""
        # Arrange
        data = CreateProductModel(name="Aurora")

        # Act
        result = await CreateProductQuery().execute(data=data, connection=self._conn)

        # Assert
        row = self._conn.execute(
            "SELECT name, description FROM products WHERE id = ?", [result.id]
        ).fetchone()
        assert row is not None
        assert row[0] == "Aurora"
        assert row[1] is None

    async def test_omitted_description_is_stored_as_null(self) -> None:
        """A missing description round-trips as ``None``."""
        # Arrange
        data = CreateProductModel(name="Aurora")

        # Act
        result = await CreateProductQuery().execute(data=data, connection=self._conn)

        # Assert
        assert result.description is None

    async def test_duplicate_name_raises_conflict(self) -> None:
        """A second product with the same name raises :class:`ConflictError`."""
        # Arrange
        data = CreateProductModel(name="Aurora")
        await CreateProductQuery().execute(data=data, connection=self._conn)

        # Act / Assert
        with self.assertRaises(ConflictError) as caught:
            await CreateProductQuery().execute(data=data, connection=self._conn)
        assert caught.exception.details == {"name": "Aurora"}
