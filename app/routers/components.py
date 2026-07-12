"""Router for the ``/components`` resource.

The shell fixes the prefix, tag, and the mandatory authenticated-principal dependency so auth is
enforced uniformly; the routes below add component creation and the immutable
per-component version history. Every database value is bound through
parameterized SQL in the query layer.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.auth.require_principal import require_principal
from app.connections.db_dependency import get_db_connection
from app.connections.db_session import DbSession
from app.models.requests.create_component_model import CreateComponentModel
from app.models.responses.component_response_model import ComponentResponseModel
from app.models.responses.version_response_model import VersionResponseModel
from app.queries.components.create_component_query import CreateComponentQuery
from app.queries.components.list_component_versions_query import ListComponentVersionsQuery
from app.queries.components.list_component_versions_request import (
    ListComponentVersionsRequest,
)

router = APIRouter(
    tags=["components"],
    prefix="/components",
    dependencies=[Depends(require_principal)],
)

DbConnection = Annotated[DbSession, Depends(get_db_connection)]


@router.post("", response_model=ComponentResponseModel, status_code=status.HTTP_201_CREATED)
async def create_component(
    payload: CreateComponentModel, connection: DbConnection
) -> ComponentResponseModel:
    """Create a component under an existing product.

    Args:
        payload: The validated create-component request body.
        connection: The application-managed DuckDB connection.

    Returns:
        The created component.

    Raises:
        NotFoundError: When ``payload.product_id`` does not exist (HTTP 404).
    """
    return await CreateComponentQuery().execute(data=payload, connection=connection)


@router.get("/{component_id}/versions", response_model=list[VersionResponseModel])
async def list_component_versions(
    component_id: str, connection: DbConnection
) -> list[VersionResponseModel]:
    """Return a component's version history, semver-descending.

    Args:
        component_id: The target component identifier.
        connection: The application-managed DuckDB connection.

    Returns:
        The component's versions ordered by ``(major, minor, patch)`` descending
        (an empty list when the component exists but has no versions).

    Raises:
        NotFoundError: When ``component_id`` does not exist (HTTP 404).
    """
    request = ListComponentVersionsRequest(component_id=component_id)
    return await ListComponentVersionsQuery().execute(data=request, connection=connection)
