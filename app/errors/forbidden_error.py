"""Typed error for an authenticated-but-not-permitted request (HTTP 403)."""

from fastapi import status

from app.errors.domain_error import DomainError
from app.errors.error_code import ErrorCode


class ForbiddenError(DomainError):
    """Raised when a caller is authenticated but not permitted to act.

    Serializes to HTTP 403 with envelope code ``forbidden`` (see
    ``docs/design/API_CONTRACT.md`` §3). For the specific "email domain is not
    on the allow-list" case, raise :class:`DomainNotAllowedError` instead so the
    client receives the ``domain_not_allowed`` code.
    """

    http_status: int = status.HTTP_403_FORBIDDEN
    code: ErrorCode = ErrorCode.FORBIDDEN
