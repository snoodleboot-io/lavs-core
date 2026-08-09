"""Response body describing a component."""

from app.models.enums.component_kind import ComponentKind
from app.models.responses.response_model import ResponseModel


class ComponentResponseModel(ResponseModel):
    """The ``Component`` schema from ``docs/design/API_CONTRACT.md`` §3."""

    id: str
    product_id: str
    name: str
    kind: ComponentKind

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "01KW8WHA6STWW5N1VYRSHDTK1N",
                    "product_id": "01KW8WHA6STWW5N1VYRSHDTK1P",
                    "name": "lavs-api",
                    "kind": "service",
                }
            ]
        }
    }
