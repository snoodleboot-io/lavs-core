"""Request body for ``POST /auth/login``."""

from typing import Annotated

from annotated_types import MinLen

from app.models.requests.request_model import RequestModel


class LoginModel(RequestModel):
    """JSON body carrying a login credential.

    Both fields are required and non-empty; a request that omits either is a
    422 (malformed) rather than a 401 (bad credentials). See
    ``docs/design/API_CONTRACT.md`` §2.
    """

    email: Annotated[str, MinLen(1)]
    password: Annotated[str, MinLen(1)]

    model_config = {
        "json_schema_extra": {
            "examples": [{"email": "engineer@example.com", "password": "correct horse battery"}]
        }
    }
