"""Enumeration of the stable error codes carried in the error envelope."""

from enum import StrEnum


class ErrorCode(StrEnum):
    """The machine-readable ``code`` field of the error envelope.

    See ``docs/design/API_CONTRACT.md`` §3 — clients branch on these stable
    codes rather than on the human-readable ``message``.
    """

    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    VALIDATION_ERROR = "validation_error"
    HTTP_ERROR = "http_error"
    INTERNAL_ERROR = "internal_error"
