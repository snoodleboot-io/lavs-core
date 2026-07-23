"""Typed error for a rate-limited request (HTTP 429)."""

from fastapi import status

from app.errors.domain_error import DomainError
from app.errors.error_code import ErrorCode


class RateLimitedError(DomainError):
    """Raised when a client exceeds the configured request rate.

    Serializes to HTTP 429 with envelope code ``rate_limited``. Used by the
    auth rate-limit middleware, which renders the envelope directly (user
    middleware runs outside the exception-handler stack) but builds it from
    this typed error so the shape stays identical to every other failure.
    """

    http_status: int = status.HTTP_429_TOO_MANY_REQUESTS
    code: ErrorCode = ErrorCode.RATE_LIMITED
