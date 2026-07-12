"""Request body for ``POST /auth/login``."""

from typing import Annotated

from annotated_types import MinLen
from pydantic import field_validator

from app.models.requests.request_model import RequestModel


class LoginModel(RequestModel):
    """JSON body carrying a login credential.

    Both fields are required and non-empty; a request that omits either is a
    422 (malformed) rather than a 401 (bad credentials). The email is normalised
    (trimmed + lower-cased) identically to sign-up so a case/whitespace variant
    of a registered address still resolves the same account. See
    ``docs/design/API_CONTRACT.md`` §2.
    """

    email: Annotated[str, MinLen(1)]
    password: Annotated[str, MinLen(1)]

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, value: str) -> str:
        """Trim and lower-case the email to match the stored form.

        Args:
            value: The raw email from the request body.

        Returns:
            The normalised (lower-cased, trimmed) email.
        """
        return value.strip().lower()

    model_config = {
        "json_schema_extra": {
            "examples": [{"email": "engineer@example.com", "password": "correct horse battery"}]
        }
    }
