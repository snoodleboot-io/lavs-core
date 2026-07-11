"""Request payload carrying everything the cut-release query needs."""

from app.models.requests.request_model import RequestModel


class CutReleaseRequest(RequestModel):
    """Inputs for ``POST /products/{product_id}/releases``.

    The route adapts the path parameter, JSON body, and optional
    ``Idempotency-Key`` header onto this single model so it satisfies the
    :class:`~app.queries.query.Query` execution contract. The server owns
    ``product_version`` derivation, so it is deliberately absent here.
    """

    product_id: str
    label: str | None = None
    notes: str | None = None
    idempotency_key: str | None = None
