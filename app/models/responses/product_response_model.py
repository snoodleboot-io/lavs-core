"""Response body describing a product."""

from app.models.responses.response_model import ResponseModel


class ProductResponseModel(ResponseModel):
    """The ``Product`` schema from ``docs/design/API_CONTRACT.md`` §3."""

    id: str
    name: str
    description: str | None
    base_version: str = "0.0.0"
    created_at: str

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "01KW8WHA6STWW5N1VYRSHDTK1N",
                    "name": "Aurora Platform",
                    "description": "The flagship product.",
                    "base_version": "0.0.0",
                    "created_at": "2026-06-29T12:00:00Z",
                }
            ]
        }
    }
