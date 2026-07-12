"""Stable identifiers for the non-human (``service``) principals LAVS mints."""

from enum import StrEnum


class ServiceIdentity(StrEnum):
    """The fixed ``id`` values carried by service principals.

    Kept as an enum rather than bare string literals so the anonymous and
    API-key identities are named in exactly one place.
    """

    ANONYMOUS = "anonymous"
    API_KEY = "api-key"
