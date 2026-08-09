"""Enumeration of the kinds of component a product may contain."""

from enum import StrEnum


class ComponentKind(StrEnum):
    """The kind of a component as defined by the API contract.

    See ``docs/design/API_CONTRACT.md`` §3 — a component's ``kind`` is one of
    ``library``, ``service``, ``ui`` or ``cli``.
    """

    LIBRARY = "library"
    SERVICE = "service"
    UI = "ui"
    CLI = "cli"
