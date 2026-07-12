"""Response body describing a user (never carries the password hash)."""

from app.models.responses.response_model import ResponseModel


class UserResponseModel(ResponseModel):
    """The safe ``User`` projection returned by the auth endpoints.

    Deliberately omits ``password_hash`` so a user's credential material can
    never leak through a response. See ``docs/design/API_CONTRACT.md`` §2.
    """

    id: str
    email: str
    status: str
    edition: str | None = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "01KW8WHA6STWW5N1VYRSHDTK1N",
                    "email": "engineer@example.com",
                    "status": "active",
                    "edition": "oss",
                }
            ]
        }
    }
