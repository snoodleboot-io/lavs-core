"""Response body for the public ``GET /meta`` capability endpoint."""

from app.models.responses.response_model import ResponseModel


class MetaResponseModel(ResponseModel):
    """Deployment capabilities the UI reads to render the right login.

    See ``docs/design/API_CONTRACT.md`` §8: the UI branches on ``edition`` and
    the enabled ``auth_modes`` (password form vs configured-key vs Stytch
    widget). Public — it must be reachable before a principal exists.
    ``stytch_public_token`` is the browser-safe publishable Stytch token the
    EE login widget initialises with; it is ``None`` outside EE/stytch
    deployments (never the project secret) and the ``/meta`` route serializes
    with ``exclude_none`` so the key is **omitted** when unset, keeping the
    OSS response body byte-identical to its pre-EE shape.
    """

    edition: str
    auth_modes: list[str]
    stytch_public_token: str | None = None

    model_config = {
        "json_schema_extra": {
            "examples": [{"edition": "oss", "auth_modes": ["password", "apikey"]}]
        }
    }
