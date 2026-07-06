"""Query that appends an immutable version and makes it the active one."""

from typing import Any

from app.errors.not_found_error import NotFoundError
from app.models.enums.version_status import VersionStatus
from app.models.requests.create_version_model import CreateVersionModel
from app.models.responses.version_response_model import VersionResponseModel
from app.models.types.ulid_id import new_ulid
from app.queries.query import Query
from app.queries.versions.version_row_mapper import to_version_response

_SELECT_COMPONENT = "SELECT id FROM components WHERE id = ?"
_SUPERSEDE_ACTIVE = "UPDATE versions SET status = ? WHERE component_id = ? AND status = ?"
_INSERT_VERSION = (
    "INSERT INTO versions "
    "(id, component_id, major, minor, patch, prerelease, status) "
    "VALUES (?, ?, ?, ?, ?, ?, ?)"
)
_SELECT_VERSION = (
    "SELECT id, component_id, major, minor, patch, prerelease, status, created_at "
    "FROM versions WHERE id = ?"
)


class CreateVersionQuery(Query[VersionResponseModel]):
    """Append an immutable version row and make it the component's active one.

    History is append-only: the newly inserted row becomes ``active`` and the
    component's previously-active version (at most one) is marked ``superseded``.
    No existing row is ever mutated beyond its ``status`` and none is deleted.
    """

    async def apply(self, data: CreateVersionModel, conn: Any) -> VersionResponseModel:
        """Insert the new version and supersede the prior active one.

        Args:
            data: The validated create-version request (component id, semver
                parts, optional prerelease).
            conn: Live database connection.

        Returns:
            The freshly created, now-active version.

        Raises:
            NotFoundError: When ``data.component_id`` does not exist.
        """
        component_rows = conn.execute(_SELECT_COMPONENT, (data.component_id,)).fetchall()
        if len(component_rows) == 0:
            raise NotFoundError(
                message=f"Component '{data.component_id}' does not exist.",
                details={"component_id": data.component_id},
            )

        # Supersede the component's currently-active version so exactly one row
        # remains active once the new version is inserted below.
        _ = conn.execute(
            _SUPERSEDE_ACTIVE,
            (VersionStatus.SUPERSEDED.value, data.component_id, VersionStatus.ACTIVE.value),
        )

        version_id = new_ulid()
        _ = conn.execute(
            _INSERT_VERSION,
            (
                version_id,
                data.component_id,
                data.major,
                data.minor,
                data.patch,
                data.prerelease,
                VersionStatus.ACTIVE.value,
            ),
        )

        created = conn.execute(_SELECT_VERSION, (version_id,))
        rows = created.fetchall()
        return to_version_response(created.description, rows[0])
