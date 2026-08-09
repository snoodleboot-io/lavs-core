"""A domain event carried on the in-process event bus and SSE stream."""

from typing import Any

from pydantic import BaseModel

from app.events.event_type import EventType


class DomainEvent(BaseModel):
    """A single domain event published for one product.

    ``event_type`` selects the SSE ``event:`` name and ``data`` carries the
    matching ``data:`` payload shape from ``docs/design/API_CONTRACT.md`` §6
    (for example ``{"component_id": ..., "version": {...}}`` for
    ``version.created`` or ``{"release": {...}}`` for ``release.cut``).
    ``product_id`` scopes fan-out so a subscriber only sees its product's events.
    """

    event_type: EventType
    product_id: str
    data: dict[str, Any]
