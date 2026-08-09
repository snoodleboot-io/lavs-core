"""Enumeration of the lifecycle status of an immutable version."""

from enum import StrEnum


class VersionStatus(StrEnum):
    """The status of a version as defined by the API contract.

    See ``docs/design/API_CONTRACT.md`` §3 — a version's ``status`` is one of
    ``active``, ``superseded`` or ``rolled_back``. Versions are append-only and
    immutable; the status records where a version sits in the rollback ledger.
    """

    ACTIVE = "active"
    SUPERSEDED = "superseded"
    ROLLED_BACK = "rolled_back"
