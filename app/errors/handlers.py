"""FastAPI exception handlers that render every error as the uniform envelope.

Register them once at startup via :func:`register_error_handlers`. Together they
guarantee that domain errors, request-validation failures, and framework
``HTTPException`` all serialize as
``{"error": {"code": ..., "message": ..., "details": {...}}}``.
"""

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.errors.domain_error import DomainError
from app.errors.error_code import ErrorCode
from app.errors.error_detail import ErrorDetail
from app.errors.error_envelope import ErrorEnvelope

# HTTP statuses that carry a more specific envelope code than the generic
# ``http_error`` fallback. Kept as a mapping (config-style) rather than inline
# magic numbers in branches.
_HTTP_STATUS_TO_CODE: dict[int, ErrorCode] = {
    status.HTTP_401_UNAUTHORIZED: ErrorCode.UNAUTHORIZED,
    status.HTTP_403_FORBIDDEN: ErrorCode.FORBIDDEN,
    status.HTTP_404_NOT_FOUND: ErrorCode.NOT_FOUND,
    status.HTTP_409_CONFLICT: ErrorCode.CONFLICT,
}


def _envelope_response(
    http_status: int, code: ErrorCode, message: str, details: dict[str, object]
) -> JSONResponse:
    """Build a ``JSONResponse`` carrying the uniform error envelope.

    Args:
        http_status: The HTTP status code for the response.
        code: The stable machine-readable error code.
        message: The human-readable error message.
        details: Structured context for the client.

    Returns:
        A ``JSONResponse`` whose body is the serialized envelope.
    """
    envelope = ErrorEnvelope(error=ErrorDetail(code=code, message=message, details=details))
    return JSONResponse(status_code=http_status, content=jsonable_encoder(envelope))


async def handle_domain_error(_request: Request, exc: DomainError) -> JSONResponse:
    """Render a typed :class:`DomainError` as the error envelope."""
    return _envelope_response(exc.http_status, exc.code, exc.message, exc.details)


async def handle_validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
    """Render a request-validation failure as a 422 envelope."""
    details: dict[str, object] = {"errors": jsonable_encoder(exc.errors())}
    return _envelope_response(
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        ErrorCode.VALIDATION_ERROR,
        "Request validation failed.",
        details,
    )


async def handle_http_exception(_request: Request, exc: HTTPException) -> JSONResponse:
    """Render a framework ``HTTPException`` as the error envelope.

    The envelope code is derived from the status (404 -> ``not_found``,
    409 -> ``conflict``); anything else falls back to ``http_error``.
    """
    code = _HTTP_STATUS_TO_CODE.get(exc.status_code, ErrorCode.HTTP_ERROR)
    message = str(exc.detail) if exc.detail is not None else "HTTP error."
    return _envelope_response(exc.status_code, code, message, {})


def register_error_handlers(application: FastAPI) -> None:
    """Register every envelope handler on the application.

    Args:
        application: The FastAPI application to attach handlers to.
    """
    application.add_exception_handler(DomainError, handle_domain_error)  # type: ignore[arg-type]
    application.add_exception_handler(
        RequestValidationError,
        handle_validation_error,  # type: ignore[arg-type]
    )
    application.add_exception_handler(HTTPException, handle_http_exception)  # type: ignore[arg-type]
