"""Request body for ``POST /auth/stytch/callback`` (EE)."""

from typing import Annotated

from annotated_types import MaxLen, MinLen

from app.models.requests.request_model import RequestModel


class StytchCallbackModel(RequestModel):
    """JSON body carrying the Stytch session credential to exchange.

    ``stytch_token`` is the session token or session JWT the Stytch frontend
    SDK produced; the backend verifies it and issues its own ``lavs_session``
    cookie (see ``docs/design/API_CONTRACT.md`` §2). Required and non-empty —
    an omitted token is a 422 (malformed) rather than a 401 (bad credentials).
    The token is never logged or persisted.
    """

    stytch_token: Annotated[str, MinLen(1), MaxLen(4096)]

    model_config = {"json_schema_extra": {"examples": [{"stytch_token": "WJtR5BCy38..."}]}}
