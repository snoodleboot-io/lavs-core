"""The lifecycle status of a user row."""

from enum import StrEnum


class UserStatus(StrEnum):
    """The ``status`` column of the ``users`` table.

    A user is created ``pending`` at sign-up, becomes ``active`` after email
    verification, and may be ``disabled`` by an operator. Mirrors the DDL
    ``CHECK`` constraint so the allowed values live in exactly one place in the
    Python layer.
    """

    PENDING = "pending"
    ACTIVE = "active"
    DISABLED = "disabled"
