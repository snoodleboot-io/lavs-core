from typing import Any

from app.models.requests.application_and_version_model import (
    ApplicationAndVersionNameModel,
)
from app.models.responses.response_model import ResponseModel
from app.queries.query import Query
from app.queries.versions.retrieve_latest_version import RetrieveLatestVersion


class DeleteVersion(Query):
    """Delete a specific version."""

    def __init__(self):
        super().__init__()
        self._latest_version_query = RetrieveLatestVersion()

    async def apply(self, data: ApplicationAndVersionNameModel, conn: Any) -> ResponseModel:
        """Delete a version from the database given the product name and its version.

        Args:
            data: Product name and version.
            conn: Live database connection.
        """
        _ = conn.sql(
            query=("DELETE FROM Versions WHERE product_name=? AND major=? AND minor=? AND patch=?"),
            params=(data.product_name, data.major, data.minor, data.patch),
        )

        return ResponseModel()
