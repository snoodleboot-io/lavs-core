"""Request body for creating a product."""

from typing import Annotated

from annotated_types import MinLen

from app.models.requests.request_model import RequestModel


class CreateProductModel(RequestModel):
    """JSON body for ``POST /products``.

    See ``docs/design/API_CONTRACT.md`` §3.
    """

    name: Annotated[str, MinLen(1)]
    description: str | None = None

    model_config = {
        "json_schema_extra": {
            "examples": [{"name": "Aurora Platform", "description": "The flagship product."}]
        }
    }
