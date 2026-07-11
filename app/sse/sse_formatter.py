"""Render a :class:`DomainEvent` as a single Server-Sent Events wire frame.

The SSE line protocol is deliberately tiny: an ``event:`` line naming the event,
a ``data:`` line carrying the JSON payload, then a blank line terminating the
frame. Keeping this translation in one function lets both the live stream and
its unit tests format events identically.
"""

import json

from app.events.domain_event import DomainEvent

_KEEP_ALIVE_FRAME = ": keep-alive\n\n"


def format_sse_frame(event: DomainEvent) -> str:
    """Format ``event`` as an SSE ``event:``/``data:`` frame.

    The ``event:`` name is the contract event type (for example
    ``version.created``) and the ``data:`` line is the compact JSON encoding of
    the event's payload. The frame ends with the mandatory blank line.

    Args:
        event: The domain event to serialise.

    Returns:
        A complete SSE frame, for example
        ``"event: version.created\\ndata: {...}\\n\\n"``.
    """
    payload = json.dumps(event.data, separators=(",", ":"))
    return f"event: {event.event_type.value}\ndata: {payload}\n\n"


def keep_alive_frame() -> str:
    """Return the SSE comment frame used as a periodic keep-alive.

    A comment line (one starting with ``:``) is ignored by ``EventSource`` but
    still forces a socket write, so a dead client surfaces as a write failure
    rather than a silently wedged connection.

    Returns:
        The ``": keep-alive\\n\\n"`` comment frame.
    """
    return _KEEP_ALIVE_FRAME
