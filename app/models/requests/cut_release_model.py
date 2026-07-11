"""Request body for cutting a release."""

from app.models.requests.request_model import RequestModel


class CutReleaseModel(RequestModel):
    """JSON body for ``POST /products/{id}/releases``.

    See ``docs/design/API_CONTRACT.md`` §5. The client may supply only an
    optional human ``label`` and free-form ``notes``; it **cannot** set the
    ``product_version`` — the server owns version derivation (default bump =
    minor, starting from the product's configured base).
    """

    label: str | None = None
    notes: str | None = None

    model_config = {
        "json_schema_extra": {"examples": [{"label": "Aurora 5.1", "notes": "optional"}]}
    }
