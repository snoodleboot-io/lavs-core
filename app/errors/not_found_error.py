"""Typed error for a missing resource (HTTP 404)."""

from fastapi import status

from app.errors.domain_error import DomainError
from app.errors.error_code import ErrorCode


class NotFoundError(DomainError):
    """Raised when a requested resource does not exist.

    Serializes to HTTP 404 with envelope code ``not_found``.
    """

    http_status: int = status.HTTP_404_NOT_FOUND
    code: ErrorCode = ErrorCode.NOT_FOUND
