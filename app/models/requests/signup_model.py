"""Request body for ``POST /auth/signup``."""

import re
from typing import Annotated

from annotated_types import MaxLen, MinLen
from pydantic import field_validator

from app.auth.signup.signup_policy import SignupPolicy
from app.models.requests.request_model import RequestModel


class SignupModel(RequestModel):
    """JSON body for ``POST /auth/signup``.

    ``EmailStr`` is intentionally not used: pydantic's email type requires the
    ``email-validator`` package, which is not a project dependency. Instead the
    email is normalised (trimmed + lower-cased) and shape-checked against
    :attr:`SignupPolicy.EMAIL_PATTERN`. See ``docs/design/API_CONTRACT.md`` §2.
    """

    email: Annotated[str, MaxLen(320)]
    password: Annotated[str, MinLen(SignupPolicy.MIN_PASSWORD_LENGTH), MaxLen(128)]

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, value: str) -> str:
        """Trim, lower-case, and shape-check the email address.

        Args:
            value: The raw email from the request body.

        Returns:
            The normalised (lower-cased, trimmed) email.

        Raises:
            ValueError: When the value is not a plausible email address.
        """
        normalized = value.strip().lower()
        if re.fullmatch(SignupPolicy.EMAIL_PATTERN, normalized) is None:
            raise ValueError("A valid email address is required.")
        return normalized

    model_config = {
        "json_schema_extra": {
            "examples": [{"email": "engineer@example.com", "password": "correct horse battery"}]
        }
    }
