"""Request body for creating a component."""

from typing import Annotated

from annotated_types import MaxLen, MinLen

from app.models.enums.component_kind import ComponentKind
from app.models.requests.request_model import RequestModel
from app.models.types.ulid_id import UlidId


class CreateComponentModel(RequestModel):
    """JSON body for ``POST /components``.

    See ``docs/design/API_CONTRACT.md`` §3.
    """

    product_id: UlidId
    name: Annotated[str, MinLen(1), MaxLen(256)]
    kind: ComponentKind

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "product_id": "01KW8WHA6STWW5N1VYRSHDTK1N",
                    "name": "lavs-api",
                    "kind": "service",
                }
            ]
        }
    }
