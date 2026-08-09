"""Typed error for a missing or invalid credential (HTTP 401)."""

from fastapi import status

from app.errors.domain_error import DomainError
from app.errors.error_code import ErrorCode


class UnauthorizedError(DomainError):
    """Raised when a request carries no valid credential.

    Serializes to HTTP 401 with envelope code ``unauthorized`` (see
    ``docs/design/API_CONTRACT.md`` §3). Raised by the auth resolver when at
    least one provider is enabled but none authenticate the request.
    """

    http_status: int = status.HTTP_401_UNAUTHORIZED
    code: ErrorCode = ErrorCode.UNAUTHORIZED
