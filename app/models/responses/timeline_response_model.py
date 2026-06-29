"""Composite response body for the Constellation timeline view."""

from app.models.responses.component_with_versions_response_model import (
    ComponentWithVersionsResponseModel,
)
from app.models.responses.product_response_model import ProductResponseModel
from app.models.responses.response_model import ResponseModel


class TimelineResponseModel(ResponseModel):
    """The composite timeline schema from ``docs/design/API_CONTRACT.md`` §3.

    Returned by ``GET /products/{id}/timeline`` — a product together with each of
    its components and that component's immutable versions, in one call.
    """

    product: ProductResponseModel
    components: list[ComponentWithVersionsResponseModel]
