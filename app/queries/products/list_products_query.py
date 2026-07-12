"""Query that lists every product."""

from app.connections.db_session import DbSession
from app.models.requests.request_model import RequestModel
from app.models.responses.product_response_model import ProductResponseModel
from app.queries.products.product_response_mapper import ProductResponseMapper
from app.queries.query import Query


class ListProductsQuery(Query[list[ProductResponseModel]]):
    """Return all products ordered by creation time (oldest first)."""

    async def apply(self, data: RequestModel, conn: DbSession) -> list[ProductResponseModel]:
        """Select and map every product row.

        Args:
            data: An empty request payload (no filter is applied).
            conn: The live DuckDB connection to run against.

        Returns:
            The full list of products; empty when none exist.
        """
        rows = conn.execute(
            "SELECT id, name, description, base_version, created_at FROM products "
            "ORDER BY created_at, id"
        ).fetchall()
        return [ProductResponseMapper.to_model(row) for row in rows]
