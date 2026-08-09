"""Typed error for a conflicting request (HTTP 409)."""

from fastapi import status

from app.errors.domain_error import DomainError
from app.errors.error_code import ErrorCode


class ConflictError(DomainError):
    """Raised when a request conflicts with the current resource state.

    Serializes to HTTP 409 with envelope code ``conflict``.
    """

    http_status: int = status.HTTP_409_CONFLICT
    code: ErrorCode = ErrorCode.CONFLICT
