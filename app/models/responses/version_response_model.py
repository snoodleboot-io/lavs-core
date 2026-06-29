"""Response body describing an immutable version."""

from typing import Annotated

from annotated_types import Ge

from app.models.enums.version_status import VersionStatus
from app.models.responses.response_model import ResponseModel


class VersionResponseModel(ResponseModel):
    """The ``Version`` schema from ``docs/design/API_CONTRACT.md`` §3."""

    id: str
    component_id: str
    major: Annotated[int, Ge(0)]
    minor: Annotated[int, Ge(0)]
    patch: Annotated[int, Ge(0)]
    prerelease: str | None
    status: VersionStatus
    created_at: str

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "01KW8WHA6STWW5N1VYRSHDTK1N",
                    "component_id": "01KW8WHA6STWW5N1VYRSHDTK1P",
                    "major": 2,
                    "minor": 4,
                    "patch": 0,
                    "prerelease": None,
                    "status": "active",
                    "created_at": "2026-06-29T12:00:00Z",
                }
            ]
        }
    }
