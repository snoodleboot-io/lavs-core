"""The top-level uniform error-envelope response model."""

from pydantic import BaseModel

from app.errors.error_detail import ErrorDetail


class ErrorEnvelope(BaseModel):
    """The uniform error response shape ``{"error": {...}}``.

    Every failure — typed domain errors, request validation, and framework
    ``HTTPException`` — serializes to this single shape. See
    ``docs/design/API_CONTRACT.md`` §3.
    """

    error: ErrorDetail
