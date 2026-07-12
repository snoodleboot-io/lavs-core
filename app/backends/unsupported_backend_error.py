"""Typed error raised when a configured backend has no registered builder."""

from app.backends.backend_kind import BackendKind


class UnsupportedBackendError(Exception):
    """Raised when :class:`BackendFactory` cannot build the selected backend.

    This is a startup/configuration failure (an enabled backend whose lane is
    not installed), not a request-time domain error, so it is a plain typed
    exception rather than a :class:`~app.errors.domain_error.DomainError`.
    """

    def __init__(self, kind: BackendKind, available: list[BackendKind]) -> None:
        """Initialise the error.

        Args:
            kind: The backend that was selected but has no registered builder.
            available: The backends that do have builders registered.
        """
        self.kind = kind
        self.available = available
        available_names = ", ".join(sorted(backend.value for backend in available))
        super().__init__(
            f"No builder registered for backend '{kind.value}'. Available: {available_names}."
        )
