"""Request payload identifying the version targeted by a rollback."""

from app.models.requests.request_model import RequestModel


class RollbackVersionRequest(RequestModel):
    """Carries the target version id for ``POST /versions/{version_id}/rollback``.

    The rollback endpoint takes no request body; this model adapts the path
    parameter to the :class:`~app.queries.query.Query` execution contract, which
    expects a :class:`~app.models.requests.request_model.RequestModel`.
    """

    version_id: str
