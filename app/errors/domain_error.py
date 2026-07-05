"""Base class for typed domain errors that serialize to the error envelope."""

from app.errors.error_code import ErrorCode


class DomainError(Exception):
    """A domain failure that maps to a uniform error-envelope response.

    Subclasses fix the HTTP status and the stable :class:`ErrorCode`; callers
    supply a human-readable ``message`` and optional structured ``details``.
    The registered exception handler reads these attributes to build the
    ``{"error": {"code", "message", "details"}}`` body.
    """

    http_status: int = 500
    code: ErrorCode = ErrorCode.INTERNAL_ERROR

    def __init__(self, message: str, details: dict[str, object] | None = None) -> None:
        """Initialise the error.

        Args:
            message: Human-readable description of the failure.
            details: Optional structured context for the client.
        """
        super().__init__(message)
        self.message = message
        self.details: dict[str, object] = details if details is not None else {}
