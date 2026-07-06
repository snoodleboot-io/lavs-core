"""Router shell for the Constellation timeline view.

Mounted under the ``/products`` prefix; the timeline lane adds
``GET /{product_id}/timeline``. The shell fixes the prefix, tag, and the
mandatory API-key dependency so auth is enforced uniformly.
"""

from typing import Annotated

import duckdb
from fastapi import APIRouter, Depends

from app.connections.db_dependency import get_db_connection
from app.errors.not_found_error import NotFoundError
from app.models.responses.timeline_response_model import TimelineResponseModel
from app.queries.timeline.timeline_query import TimelineQuery
from app.queries.timeline.timeline_request_model import TimelineRequestModel
from app.security.api_key import get_api_key

router = APIRouter(
    tags=["timeline"],
    prefix="/products",
    dependencies=[Depends(get_api_key)],
)


@router.get("/{product_id}/timeline")
async def get_timeline(
    product_id: str,
    connection: Annotated[duckdb.DuckDBPyConnection, Depends(get_db_connection)],
) -> TimelineResponseModel:
    """Return a product with its components and their versions in one call.

    Args:
        product_id: The identifier of the product to assemble the timeline for.
        connection: The application-managed DuckDB connection.

    Returns:
        The composite timeline for the product.

    Raises:
        NotFoundError: When no product carries ``product_id``.
    """
    timeline = await TimelineQuery().execute(
        TimelineRequestModel(product_id=product_id), connection
    )
    if timeline is None:
        raise NotFoundError("Product not found.", {"product_id": product_id})
    return timeline
