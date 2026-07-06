"""Routes for the ``/versions`` resource: immutable create and rollback.

The router shell fixes the prefix, tag, and mandatory API-key dependency; this
module fills in the two lifecycle endpoints:

* ``POST /versions`` -- append an immutable version, making it the component's
  active one and superseding the prior active version.
* ``POST /versions/{version_id}/rollback`` -- non-destructively roll a version
  back to its predecessor, re-activating the previous version.
"""

from typing import Annotated

import duckdb
from fastapi import APIRouter, Depends

from app.connections.db_dependency import get_db_connection
from app.models.requests.create_version_model import CreateVersionModel
from app.models.responses.version_response_model import VersionResponseModel
from app.queries.versions.create_version_query import CreateVersionQuery
from app.queries.versions.rollback_version_query import RollbackVersionQuery
from app.queries.versions.rollback_version_request import RollbackVersionRequest
from app.security.api_key import get_api_key

router = APIRouter(
    tags=["versions"],
    prefix="/versions",
    dependencies=[Depends(get_api_key)],
)

DbConnection = Annotated[duckdb.DuckDBPyConnection, Depends(get_db_connection)]


@router.post("", response_model=VersionResponseModel)
async def create_version(
    body: CreateVersionModel, connection: DbConnection
) -> VersionResponseModel:
    """Append an immutable version and make it the component's active one.

    Args:
        body: The create-version request (component id, semver, optional prerelease).
        connection: The application-managed DuckDB connection.

    Returns:
        The newly created, now-active version.
    """
    return await CreateVersionQuery().execute(data=body, connection=connection)


@router.post("/{version_id}/rollback", response_model=VersionResponseModel)
async def rollback_version(version_id: str, connection: DbConnection) -> VersionResponseModel:
    """Roll a version back to its predecessor, re-activating the previous one.

    Args:
        version_id: The id of the version to roll back.
        connection: The application-managed DuckDB connection.

    Returns:
        The previous version, now re-activated as the component's active one.
    """
    return await RollbackVersionQuery().execute(
        data=RollbackVersionRequest(version_id=version_id), connection=connection
    )
