"""Typed error for a sign-up email whose domain is not allow-listed (HTTP 403)."""

from fastapi import status

from app.errors.domain_error import DomainError
from app.errors.error_code import ErrorCode


class DomainNotAllowedError(DomainError):
    """Raised when a sign-up email's domain is not on the configured allow-list.

    Serializes to HTTP 403 with envelope code ``domain_not_allowed`` (see
    ``docs/design/API_CONTRACT.md`` §2). Provided here as part of the shared
    auth spine so the password sign-up lane (R1) can raise it directly.
    """

    http_status: int = status.HTTP_403_FORBIDDEN
    code: ErrorCode = ErrorCode.DOMAIN_NOT_ALLOWED
