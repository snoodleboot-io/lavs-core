"""Router shell for the ``releases`` resource.

Deliberately carries **no prefix**: releases are addressed under two roots —
``/products/{id}/releases`` (list + cut) and ``/releases/{id}`` (read one) — so
each route declares its full path. The shell fixes only the tag and the
mandatory API-key dependency; the cut/list routes are added by the release-write
lane and the read route by the release-read lane.
"""

from typing import Annotated

import duckdb
from fastapi import APIRouter, Depends

from app.connections.db_dependency import get_db_connection
from app.models.responses.release_response_model import ReleaseResponseModel
from app.queries.products.product_id_request import ProductIdRequest
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
