"""The inner ``error`` object of the uniform error envelope."""

from pydantic import BaseModel

from app.errors.error_code import ErrorCode


class ErrorDetail(BaseModel):
    """The body of the ``error`` key in the envelope.

    See ``docs/design/API_CONTRACT.md`` §3.
    """

    code: ErrorCode
    message: str
    details: dict[str, object] = {}
