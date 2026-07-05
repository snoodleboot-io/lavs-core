"""Request payload for the composite timeline read query."""

from app.models.requests.request_model import RequestModel


class TimelineRequestModel(RequestModel):
    """Identifies the product whose timeline is being assembled.

    Carries the path ``product_id`` from ``GET /products/{product_id}/timeline``
    into :class:`~app.queries.timeline.timeline_query.TimelineQuery`.
    """

    product_id: str
