"""Query that lists the components belonging to one product."""

from app.connections.db_session import DbSession
from app.models.enums.component_kind import ComponentKind
from app.models.responses.component_response_model import ComponentResponseModel
from app.queries.products.product_id_request import ProductIdRequest
from app.queries.query import Query


class ListComponentsByProductQuery(Query[list[ComponentResponseModel]]):
    """Return every component whose ``product_id`` matches the request.

    The caller is expected to have already confirmed the parent product exists
    (so an unknown product yields 404, not an empty list); this query simply
    returns the — possibly empty — set of components for that product.
    """

    async def apply(self, data: ProductIdRequest, conn: DbSession) -> list[ComponentResponseModel]:
        """Select the components for ``data.product_id``.

        Args:
            data: The request carrying the parent product's ULID.
            conn: The live DuckDB connection to run against.

        Returns:
            The product's components; empty when it has none.
        """
        rows = conn.execute(
            "SELECT id, product_id, name, kind FROM components "
            "WHERE product_id = ? ORDER BY name, id",
            [data.product_id],
        ).fetchall()
        return [
            ComponentResponseModel(
                id=str(row[0]),
                product_id=str(row[1]),
                name=str(row[2]),
                kind=ComponentKind(str(row[3])),
            )
            for row in rows
        ]
