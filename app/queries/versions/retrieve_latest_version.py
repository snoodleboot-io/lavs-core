from typing import Any

from app.models.requests.application_name_model import ApplicationNameModel
from app.models.responses.application_and_version_response_model import (
    ApplicationAndVersionResponseModel,
)
from app.queries.query import Query


def _row_to_response(
    description: list[tuple[Any, ...]], row: tuple[Any, ...]
) -> ApplicationAndVersionResponseModel:
    """Build a response model from a single query result row.

    Args:
        description: Column descriptions from cursor.
        row: A single result row from query execution.

    Returns:
        The response model populated from the row's columns.
    """
    columns = [desc[0] for desc in description]
    fields = dict(zip(columns, row, strict=False))
    return ApplicationAndVersionResponseModel(
        product_name=fields["product_name"],
        major=fields["major"],
        minor=fields["minor"],
        patch=fields["patch"],
        id=fields["id"],
    )


class RetrieveLatestVersion(Query):
    """Retrieve latest version of a product."""

    def __init__(self):
        """Construct an instance of RetrieveLatestVersion."""
        super().__init__()

    async def apply(
        self, data: ApplicationNameModel, conn: Any
    ) -> ApplicationAndVersionResponseModel | None:
        """Retrieve the latest version of a product.

        Args:
            data: Product name.
            conn: Live database connection.

        Returns:
            ApplicationAndVersionResponseModel if found, None otherwise.
        """
        query_result = conn.sql(
            "SELECT * FROM Versions "
            "WHERE product_name = ? "
            "AND status = ? "
            "ORDER BY major DESC, minor DESC, patch DESC "
            "LIMIT 1",
            params=(data.product_name, "active"),
        )
        rows = query_result.fetchall()
        if len(rows) > 0:
            return _row_to_response(query_result.description, rows[0])
        return None
