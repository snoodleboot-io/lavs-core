"""Query that inserts a new component and returns its response representation."""

import duckdb

from app.errors.not_found_error import NotFoundError
from app.models.requests.create_component_model import CreateComponentModel
from app.models.responses.component_response_model import ComponentResponseModel
from app.models.types.ulid_id import new_ulid
from app.queries.query import Query

_SELECT_PRODUCT_BY_ID = "SELECT id FROM products WHERE id = ?"
_INSERT_COMPONENT = "INSERT INTO components (id, product_id, name, kind) VALUES (?, ?, ?, ?)"


class CreateComponentQuery(Query[ComponentResponseModel]):
    """Create a component for an existing product.

    The parent product is looked up first so a missing product surfaces as a
    typed :class:`NotFoundError` (HTTP 404) rather than a raw foreign-key
    violation. A fresh ULID is minted for the new component and the row is
    inserted with a fully parameterized statement.
    """

    async def apply(
        self, data: CreateComponentModel, conn: duckdb.DuckDBPyConnection
    ) -> ComponentResponseModel:
        """Insert the component and return its response model.

        Args:
            data: The validated create-component request body.
            conn: The live DuckDB connection to run against.

        Returns:
            The persisted component as a :class:`ComponentResponseModel`.

        Raises:
            NotFoundError: When ``data.product_id`` does not identify a product.
        """
        product = conn.execute(_SELECT_PRODUCT_BY_ID, [data.product_id]).fetchone()
        if product is None:
            raise NotFoundError(
                message=f"Product '{data.product_id}' does not exist.",
                details={"product_id": data.product_id},
            )

        component_id = new_ulid()
        conn.execute(
            _INSERT_COMPONENT,
            [component_id, data.product_id, data.name, data.kind.value],
        )

        return ComponentResponseModel(
            id=component_id,
            product_id=data.product_id,
            name=data.name,
            kind=data.kind,
        )
