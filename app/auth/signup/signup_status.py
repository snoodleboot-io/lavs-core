"""The accepted-sign-up status returned by ``POST /auth/signup``."""

from enum import StrEnum


class SignupStatus(StrEnum):
    """The ``status`` field of the 202 sign-up acknowledgement.

    A single member today (``pending_verification``); modelled as an enum so the
    wire value lives in one place rather than as a bare string literal in the
    route and the response model.
    """

    PENDING_VERIFICATION = "pending_verification"
