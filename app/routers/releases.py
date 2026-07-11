"""Router shell for the ``releases`` resource.

Deliberately carries **no prefix**: releases are addressed under two roots —
``/products/{id}/releases`` (list + cut) and ``/releases/{id}`` (read one) — so
each route declares its full path. The shell fixes only the tag and the
mandatory API-key dependency; the cut/list routes are added by the release-write
lane and the read route by the release-read lane.
"""

from typing import Annotated

import duckdb
from fastapi import APIRouter, Depends, Header

from app.connections.db_dependency import get_db_connection
from app.events.domain_event import DomainEvent
from app.events.event_bus import EventBus
from app.events.event_bus_dependency import get_event_bus
from app.events.event_type import EventType
from app.models.requests.cut_release_model import CutReleaseModel
from app.models.responses.release_response_model import ReleaseResponseModel
from app.queries.products.product_id_request import ProductIdRequest
from app.queries.releases.cut_release_query import CutReleaseQuery
from app.queries.releases.cut_release_request import CutReleaseRequest
from app.queries.releases_read.get_release_by_id_query import GetReleaseByIdQuery
from app.queries.releases_read.list_releases_by_product_query import (
    ListReleasesByProductQuery,
)
from app.queries.releases_read.release_id_request import ReleaseIdRequest
from app.security.api_key import get_api_key

router = APIRouter(
    tags=["releases"],
    dependencies=[Depends(get_api_key)],
)

DbConnection = Annotated[duckdb.DuckDBPyConnection, Depends(get_db_connection)]
Events = Annotated[EventBus, Depends(get_event_bus)]


@router.post(
    "/products/{product_id}/releases",
    status_code=201,
    response_model=ReleaseResponseModel,
)
async def cut_release(
    product_id: str,
    body: CutReleaseModel,
    connection: DbConnection,
    event_bus: Events,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> ReleaseResponseModel:
    """Cut an immutable release freezing the product's current composition.

    Snapshots each component's ``active`` version, derives the server-owned
    ``product_version`` (default bump: minor), and persists the immutable
    release + pinned manifest. A repeated ``Idempotency-Key`` replays the
    existing release without cutting a second one. A ``release.cut`` event is
    emitted only for a fresh cut.

    Args:
        product_id: The product to cut a release for.
        body: The optional human ``label`` and free-form ``notes``.
        connection: The application-managed DuckDB connection.
        event_bus: The application-managed event bus.
        idempotency_key: Optional ``Idempotency-Key`` header deduplicating cuts.

    Returns:
        The frozen release with its pinned component manifest.
    """
    request = CutReleaseRequest(
        product_id=product_id,
        label=body.label,
        notes=body.notes,
        idempotency_key=idempotency_key,
    )
    result = await CutReleaseQuery().execute(data=request, connection=connection)
    if result.created:
        await event_bus.publish(
            DomainEvent(
                event_type=EventType.RELEASE_CUT,
                product_id=product_id,
                data={"release": result.release.model_dump()},
            )
        )
    return result.release


@router.get(
    "/products/{product_id}/releases",
    response_model=list[ReleaseResponseModel],
)
async def list_product_releases(
    product_id: str,
    conn: DbConnection,
) -> list[ReleaseResponseModel]:
    """List a product's release ledger, newest first.

    Each release carries its full frozen manifest (the components pinned at cut
    time). The product's existence is asserted first so an unknown product
    yields 404 rather than a misleading empty list.

    Args:
        product_id: The parent product's ULID string.
        conn: The application-managed DuckDB connection.

    Returns:
        The product's releases newest-first; an empty list when it has none.

    Raises:
        NotFoundError: When no product carries the given id.
    """
    return await ListReleasesByProductQuery().execute(
        data=ProductIdRequest(product_id=product_id), connection=conn
    )


@router.get("/releases/{release_id}", response_model=ReleaseResponseModel)
async def get_release(
    release_id: str,
    conn: DbConnection,
) -> ReleaseResponseModel:
    """Retrieve a single release by its ULID, with its frozen manifest.

    Args:
        release_id: The target release's ULID string.
        conn: The application-managed DuckDB connection.

    Returns:
        The matching release and its frozen manifest.

    Raises:
        NotFoundError: When no release carries the given id.
    """
    return await GetReleaseByIdQuery().execute(
        data=ReleaseIdRequest(release_id=release_id), connection=conn
    )
