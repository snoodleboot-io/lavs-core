"""Routes for the ``/versions`` resource: immutable create and rollback.

The router shell fixes the prefix, tag, and mandatory authenticated-principal dependency; this
module fills in the two lifecycle endpoints:

* ``POST /versions`` -- append an immutable version, making it the component's
  active one and superseding the prior active version.
* ``POST /versions/{version_id}/rollback`` -- non-destructively roll a version
  back to its predecessor, re-activating the previous version.
"""

from typing import Annotated

import duckdb
from fastapi import APIRouter, Depends

from app.auth.require_principal import require_principal
from app.connections.db_dependency import get_db_connection
from app.events.event_bus import EventBus
from app.events.event_bus_dependency import get_event_bus
from app.models.requests.create_version_model import CreateVersionModel
from app.models.responses.version_response_model import VersionResponseModel
from app.queries.versions.create_version_query import CreateVersionQuery
from app.queries.versions.rollback_version_query import RollbackVersionQuery
from app.queries.versions.rollback_version_request import RollbackVersionRequest

router = APIRouter(
    tags=["versions"],
    prefix="/versions",
    dependencies=[Depends(require_principal)],
)

DbConnection = Annotated[duckdb.DuckDBPyConnection, Depends(get_db_connection)]
Bus = Annotated[EventBus, Depends(get_event_bus)]


@router.post("", response_model=VersionResponseModel)
async def create_version(
    body: CreateVersionModel, connection: DbConnection, event_bus: Bus
) -> VersionResponseModel:
    """Append an immutable version and make it the component's active one.

    On success a ``version.created`` event is published on the event bus for the
    component's product so live SSE subscribers observe the new version.

    Args:
        body: The create-version request (component id, semver, optional prerelease).
        connection: The application-managed DuckDB connection.
        event_bus: The application-managed event bus.

    Returns:
        The newly created, now-active version.
    """
    return await CreateVersionQuery(event_bus).execute(data=body, connection=connection)


@router.post("/{version_id}/rollback", response_model=VersionResponseModel)
async def rollback_version(
    version_id: str, connection: DbConnection, event_bus: Bus
) -> VersionResponseModel:
    """Roll a version back to its predecessor, re-activating the previous one.

    On success a ``version.rolled_back`` event is published on the event bus for
    the component's product so live SSE subscribers observe the rollback.

    Args:
        version_id: The id of the version to roll back.
        connection: The application-managed DuckDB connection.
        event_bus: The application-managed event bus.

    Returns:
        The previous version, now re-activated as the component's active one.
    """
    return await RollbackVersionQuery(event_bus).execute(
        data=RollbackVersionRequest(version_id=version_id), connection=connection
    )
