"""Response body for the public ``GET /meta`` capability endpoint."""

from app.models.responses.response_model import ResponseModel


class MetaResponseModel(ResponseModel):
    """Deployment capabilities the UI reads to render the right login.

    See ``docs/design/API_CONTRACT.md`` §8: the UI branches on ``edition`` and
    the enabled ``auth_modes`` (password form vs configured-key vs Stytch
    widget). Public — it must be reachable before a principal exists.
    """

    edition: str
    auth_modes: list[str]

    model_config = {
        "json_schema_extra": {
            "examples": [{"edition": "oss", "auth_modes": ["password", "apikey"]}]
        }
    }
