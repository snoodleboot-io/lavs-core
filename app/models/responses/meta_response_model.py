"""Response body for the public ``GET /meta`` capability endpoint."""

from app.models.responses.response_model import ResponseModel


class MetaResponseModel(ResponseModel):
    """Deployment capabilities the UI reads to render the right login.

    See ``docs/design/API_CONTRACT.md`` §8: the UI branches on ``edition`` and
    the enabled ``auth_modes`` (password form vs configured-key). Public — it
    must be reachable before a principal exists.

    The model allows **extra** fields (``extra="allow"``) so an out-of-core
    edition can contribute additional capability fields through the ``/meta``
    plugin extension seam (``app.state.meta_extensions``) without core knowing
    their names. With no extension installed the response carries only
    ``edition`` and ``auth_modes``, byte-identical to the OSS shape.
    """

    edition: str
    auth_modes: list[str]

    model_config = {
        "extra": "allow",
        "json_schema_extra": {
            "examples": [{"edition": "oss", "auth_modes": ["password", "apikey"]}]
        },
    }
