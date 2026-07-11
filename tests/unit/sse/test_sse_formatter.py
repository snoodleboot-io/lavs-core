"""Unit tests for the SSE frame formatter."""

import json

from app.events.domain_event import DomainEvent
from app.events.event_type import EventType
from app.sse.sse_formatter import format_sse_frame, keep_alive_frame

PRODUCT_ID = "01AAAAAAAAAAAAAAAAAAAAAAAA"
COMPONENT_ID = "01CCCCCCCCCCCCCCCCCCCCCCCC"


def test_format_sse_frame_uses_event_type_as_event_name() -> None:
    """The ``event:`` line carries the contract event-type value."""
    # Arrange
    event = DomainEvent(
        event_type=EventType.VERSION_CREATED,
        product_id=PRODUCT_ID,
        data={"component_id": COMPONENT_ID, "version": {"major": 1}},
    )

    # Act
    frame = format_sse_frame(event)

    # Assert
    assert frame.startswith("event: version.created\n")
    assert frame.endswith("\n\n")


def test_format_sse_frame_data_line_is_json_payload() -> None:
    """The ``data:`` line is the JSON encoding of the event payload."""
    # Arrange
    payload = {"component_id": COMPONENT_ID, "version_id": "v1", "reactivated_version_id": "v0"}
    event = DomainEvent(
        event_type=EventType.VERSION_ROLLED_BACK, product_id=PRODUCT_ID, data=payload
    )

    # Act
    frame = format_sse_frame(event)

    # Assert
    data_line = frame.split("\n")[1]
    assert data_line.startswith("data: ")
    assert json.loads(data_line.removeprefix("data: ")) == payload


def test_format_sse_frame_matches_full_wire_shape() -> None:
    """A frame is exactly ``event:`` + ``data:`` + terminating blank line."""
    # Arrange
    event = DomainEvent(
        event_type=EventType.RELEASE_CUT, product_id=PRODUCT_ID, data={"release": {"id": "r1"}}
    )

    # Act
    frame = format_sse_frame(event)

    # Assert
    assert frame == 'event: release.cut\ndata: {"release":{"id":"r1"}}\n\n'


def test_keep_alive_frame_is_an_sse_comment() -> None:
    """The keep-alive frame is an ignored SSE comment line."""
    # Arrange / Act
    frame = keep_alive_frame()

    # Assert
    assert frame == ": keep-alive\n\n"
