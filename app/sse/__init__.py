"""Server-Sent Events helpers: frame formatting and the live event stream.

This package turns :class:`~app.events.domain_event.DomainEvent` values fanned
out by the in-process :class:`~app.events.event_bus.EventBus` into the wire
frames a browser ``EventSource`` consumes on
``GET /products/{id}/events`` (see ``docs/design/API_CONTRACT.md`` §6).
"""
