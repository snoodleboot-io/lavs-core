"""Request body for creating a product."""

from typing import Annotated

from annotated_types import MaxLen, MinLen

from app.models.requests.request_model import RequestModel


class CreateProductModel(RequestModel):
    """JSON body for ``POST /products``.

    See ``docs/design/API_CONTRACT.md`` §3.
    """

    name: Annotated[str, MinLen(1), MaxLen(256)]
    description: Annotated[str, MaxLen(4096)] | None = None

    model_config = {
        "json_schema_extra": {
            "examples": [{"name": "Aurora Platform", "description": "The flagship product."}]
        }
    }
