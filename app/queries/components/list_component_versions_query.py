"""Query returning the immutable version history for a single component."""

from datetime import datetime

from app.connections.db_session import DbSession
from app.errors.not_found_error import NotFoundError
from app.models.responses.version_response_model import VersionResponseModel
from app.queries.components.list_component_versions_request import (
    ListComponentVersionsRequest,
)
from app.queries.query import Query

_SELECT_COMPONENT_BY_ID = "SELECT id FROM components WHERE id = ?"
_SELECT_VERSIONS = (
    "SELECT id, component_id, major, minor, patch, prerelease, status, created_at "
    "FROM versions WHERE component_id = ? "
    "ORDER BY major DESC, minor DESC, patch DESC"
)


class ListComponentVersionsQuery(Query[list[VersionResponseModel]]):
    """Return a component's versions ordered by semver, newest first.

    The component is verified to exist first so an unknown component surfaces
    as a typed :class:`NotFoundError` (HTTP 404); a known component with no
    versions yields an empty list. Rows are ordered by ``(major, minor, patch)``
    descending.
    """

    async def apply(
        self, data: ListComponentVersionsRequest, conn: DbSession
    ) -> list[VersionResponseModel]:
        """Fetch the version history for ``data.component_id``.

        Args:
            data: The request carrying the target component id.
            conn: The live DuckDB connection to run against.

        Returns:
            The component's versions as response models, semver-descending.

        Raises:
            NotFoundError: When ``data.component_id`` does not identify a component.
        """
        component = conn.execute(_SELECT_COMPONENT_BY_ID, [data.component_id]).fetchone()
        if component is None:
            raise NotFoundError(
                message=f"Component '{data.component_id}' does not exist.",
                details={"component_id": data.component_id},
            )

        rows = conn.execute(_SELECT_VERSIONS, [data.component_id]).fetchall()
        return [
            VersionResponseModel(
                id=row[0],
                component_id=row[1],
                major=row[2],
                minor=row[3],
                patch=row[4],
                prerelease=row[5],
                status=row[6],
                created_at=row[7].isoformat() if isinstance(row[7], datetime) else str(row[7]),
            )
            for row in rows
        ]
