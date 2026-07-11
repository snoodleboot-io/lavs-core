"""Non-destructive rollback: re-activate the previous version, never delete."""

from typing import Any

from app.errors.conflict_error import ConflictError
from app.errors.not_found_error import NotFoundError
from app.events.domain_event import DomainEvent
from app.events.event_bus import EventBus
from app.events.event_type import EventType
from app.models.enums.version_status import VersionStatus
from app.models.responses.version_response_model import VersionResponseModel
from app.queries.query import Query
from app.queries.versions.rollback_version_request import RollbackVersionRequest
from app.queries.versions.version_row_mapper import to_version_response

_SELECT_COMPONENT_PRODUCT = "SELECT product_id FROM components WHERE id = ?"
_SELECT_BY_ID = (
    "SELECT id, component_id, major, minor, patch, prerelease, status, created_at "
    "FROM versions WHERE id = ?"
)
# The "previous version" is the highest-semver row of the same component that is
# strictly below the target, is not already rolled back, and is not the target.
_SELECT_PREVIOUS = (
    "SELECT id, component_id, major, minor, patch, prerelease, status, created_at "
    "FROM versions "
    "WHERE component_id = ? "
    "AND id <> ? "
    "AND status <> ? "
    "AND (major, minor, patch) < (?, ?, ?) "
    "ORDER BY major DESC, minor DESC, patch DESC "
    "LIMIT 1"
)
_MARK_STATUS = "UPDATE versions SET status = ? WHERE id = ?"
_SUPERSEDE_ACTIVE = "UPDATE versions SET status = ? WHERE component_id = ? AND status = ?"


class RollbackVersionQuery(Query[VersionResponseModel]):
    """Roll a version back to its predecessor without deleting any history.

    The target is marked ``rolled_back``; the previous version is re-activated.
    Any other currently-active row of the component is marked ``superseded`` so
    exactly one ``active`` row remains. No row is ever deleted.

    When an :class:`EventBus` is supplied, a ``version.rolled_back`` domain event
    is published for the component's product after the rollback commits; the
    returned response is unaffected either way.
    """

    def __init__(self, event_bus: EventBus | None = None) -> None:
        """Create the query, optionally wired to an event bus.

        Args:
            event_bus: The event bus to publish ``version.rolled_back`` on, or
                ``None`` to run without emitting events.
        """
        super().__init__()
        self._event_bus = event_bus

    async def apply(self, data: RollbackVersionRequest, conn: Any) -> VersionResponseModel:
        """Roll the target version back, re-activating the previous version.

        Args:
            data: The rollback request carrying the target ``version_id``.
            conn: Live database connection.

        Returns:
            The previous version, now re-activated as the component's active one.

        Raises:
            NotFoundError: When ``data.version_id`` does not exist.
            ConflictError: When the target has no prior version to roll back to.
        """
        target_result = conn.execute(_SELECT_BY_ID, (data.version_id,))
        target_rows = target_result.fetchall()
        if len(target_rows) == 0:
            raise NotFoundError(
                message=f"Version '{data.version_id}' does not exist.",
                details={"version_id": data.version_id},
            )
        target = to_version_response(target_result.description, target_rows[0])

        previous_result = conn.execute(
            _SELECT_PREVIOUS,
            (
                target.component_id,
                target.id,
                VersionStatus.ROLLED_BACK.value,
                target.major,
                target.minor,
                target.patch,
            ),
        )
        previous_rows = previous_result.fetchall()
        if len(previous_rows) == 0:
            raise ConflictError(
                message=f"Version '{data.version_id}' has no prior version to roll back to.",
                details={"version_id": data.version_id},
            )
        previous = to_version_response(previous_result.description, previous_rows[0])

        # Mark the target rolled back -- never deleted.
        _ = conn.execute(_MARK_STATUS, (VersionStatus.ROLLED_BACK.value, target.id))
        # Ensure no other row of this component stays active before re-activating.
        _ = conn.execute(
            _SUPERSEDE_ACTIVE,
            (VersionStatus.SUPERSEDED.value, target.component_id, VersionStatus.ACTIVE.value),
        )
        # Re-activate the previous version so exactly one active row remains.
        _ = conn.execute(_MARK_STATUS, (VersionStatus.ACTIVE.value, previous.id))

        reactivated = conn.execute(_SELECT_BY_ID, (previous.id,))
        reactivated_rows = reactivated.fetchall()
        reactivated_version = to_version_response(reactivated.description, reactivated_rows[0])

        if self._event_bus is not None:
            product_row = conn.execute(_SELECT_COMPONENT_PRODUCT, (target.component_id,)).fetchone()
            product_id: str = product_row[0]
            await self._event_bus.publish(
                DomainEvent(
                    event_type=EventType.VERSION_ROLLED_BACK,
                    product_id=product_id,
                    data={
                        "component_id": target.component_id,
                        "version_id": target.id,
                        "reactivated_version_id": reactivated_version.id,
                    },
                )
            )

        return reactivated_version
