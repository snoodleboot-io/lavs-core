from typing import Any

from app.models.requests.application_and_version_model import (
    ApplicationAndVersionNameModel,
)
from app.models.responses.application_and_version_response_model import (
    ApplicationAndVersionResponseModel,
)
from app.queries.query import Query
from app.queries.versions.retrieve_latest_version import RetrieveLatestVersion


class CreatePatch(Query):
    """Create a patch to a version."""

    def __init__(self):
        """Construct an instance of CreatePatch."""
        super().__init__()
        self._latest_version_query = RetrieveLatestVersion()

    async def apply(
        self, data: ApplicationAndVersionNameModel, conn: Any
    ) -> ApplicationAndVersionResponseModel:
        """Update product with a new patch number - incrementing by one.

        Args:
            data: Product name and version.
            conn: Live database connection.
        """
        latest_version_result = await self._latest_version_query.execute(data=data)

        if latest_version_result is None:
            raise ValueError(
                f"No version found for product '{data.product_name}'. "
                "Create a base version first using POST /versions/"
            )

        conn.sql(
            query=(
                "INSERT INTO Versions "
                "(major, minor, patch, product_name, id) "
                "VALUES (?, ?, ?, ?, nextval('version_id_seq'))"
            ),
            params=(
                latest_version_result.major,
                latest_version_result.minor,
                latest_version_result.patch + 1,
                latest_version_result.product_name,
            ),
        )
        new_latest_version: ApplicationAndVersionResponseModel = (
            await self._latest_version_query.execute(data=data)
        )
        self._logger.info(new_latest_version)

        return new_latest_version
