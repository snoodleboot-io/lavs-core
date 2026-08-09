"""Request body for ``POST /auth/verify``."""

from typing import Annotated

from annotated_types import MaxLen, MinLen

from app.models.requests.request_model import RequestModel


class VerifyModel(RequestModel):
    """JSON body for ``POST /auth/verify``.

    Carries the raw verification token delivered by email. The token is hashed
    before any lookup; the raw value is never persisted. See
    ``docs/design/API_CONTRACT.md`` §2.
    """

    token: Annotated[str, MinLen(1), MaxLen(256)]

    model_config = {"json_schema_extra": {"examples": [{"token": "Xy8f…opaque-url-safe-token"}]}}
