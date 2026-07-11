"""Query that appends an immutable version and makes it the active one."""

from typing import Any

from app.errors.not_found_error import NotFoundError
from app.events.domain_event import DomainEvent
from app.events.event_bus import EventBus
from app.events.event_type import EventType
from app.models.enums.version_status import VersionStatus
from app.models.requests.create_version_model import CreateVersionModel
from app.models.responses.version_response_model import VersionResponseModel
from app.models.types.ulid_id import new_ulid
from app.queries.query import Query
from app.queries.versions.version_row_mapper import to_version_response

_SELECT_COMPONENT = "SELECT id, product_id FROM components WHERE id = ?"
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

    When an :class:`EventBus` is supplied, a ``version.created`` domain event is
    published for the component's product after the row is committed; the
    returned response is unaffected either way.
    """

    def __init__(self, event_bus: EventBus | None = None) -> None:
        """Create the query, optionally wired to an event bus.

        Args:
            event_bus: The event bus to publish ``version.created`` on, or
                ``None`` to run without emitting events.
        """
        super().__init__()
        self._event_bus = event_bus

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
        product_id: str = component_rows[0][1]

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
        version = to_version_response(created.description, rows[0])

        if self._event_bus is not None:
            await self._event_bus.publish(
                DomainEvent(
                    event_type=EventType.VERSION_CREATED,
                    product_id=product_id,
                    data={
                        "component_id": version.component_id,
                        "version": version.model_dump(mode="json"),
                    },
                )
            )

        return version
