"""Response body acknowledging an accepted sign-up (HTTP 202)."""

from app.auth.signup.signup_status import SignupStatus
from app.models.responses.response_model import ResponseModel


class SignupAcceptedModel(ResponseModel):
    """The 202 acknowledgement for ``POST /auth/signup``.

    Deliberately reveals nothing about whether the address pre-existed beyond
    the 409 the contract mandates: a successful sign-up always returns the same
    ``pending_verification`` status. See ``docs/design/API_CONTRACT.md`` §2.
    """

    status: SignupStatus = SignupStatus.PENDING_VERIFICATION

    model_config = {"json_schema_extra": {"examples": [{"status": "pending_verification"}]}}
