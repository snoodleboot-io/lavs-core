"""Request payload carrying a single release identifier.

The read-by-id query addresses one release by its ULID; it receives this typed
payload through :meth:`Query.execute`, which requires a
:class:`~app.models.requests.request_model.RequestModel`. It lives beside the
release-read queries because it is an internal query input, not part of the
public HTTP request surface.
"""

from app.models.requests.request_model import RequestModel


class ReleaseIdRequest(RequestModel):
    """Carries the ULID string identifying the target release."""

    release_id: str
