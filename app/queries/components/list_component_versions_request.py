"""Internal query input carrying the component id for a version-history read."""

from app.models.requests.request_model import RequestModel


class ListComponentVersionsRequest(RequestModel):
    """Input for :class:`ListComponentVersionsQuery`.

    The version-history read is keyed by a path parameter rather than a JSON
    body, so this thin request model exists only to hand the ``component_id``
    to the :class:`~app.queries.query.Query` execution contract.
    """

    component_id: str
