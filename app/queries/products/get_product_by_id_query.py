"""Query that fetches a single product by its ULID identifier."""

import duckdb

from app.errors.not_found_error import NotFoundError
from app.models.responses.product_response_model import ProductResponseModel
from app.queries.products.product_id_request import ProductIdRequest
from app.queries.products.product_response_mapper import ProductResponseMapper
from app.queries.query import Query


class GetProductByIdQuery(Query[ProductResponseModel]):
    """Return one product, or raise :class:`NotFoundError` when absent.

    Reused by the components route to assert the parent product exists before
    its components are listed, so a missing product yields HTTP 404 uniformly.
    """

    async def apply(
        self, data: ProductIdRequest, conn: duckdb.DuckDBPyConnection
    ) -> ProductResponseModel:
        """Fetch the product identified by ``data.product_id``.

        Args:
            data: The request carrying the target product's ULID.
            conn: The live DuckDB connection to run against.

        Returns:
            The matching product as a response model.

        Raises:
            NotFoundError: When no product carries the requested id.
        """
        row = conn.execute(
            "SELECT id, name, description, created_at FROM products WHERE id = ?",
            [data.product_id],
        ).fetchone()
        if row is None:
            raise NotFoundError(
                message=f"No product exists with id '{data.product_id}'.",
                details={"id": data.product_id},
            )
        return ProductResponseMapper.to_model(row)
