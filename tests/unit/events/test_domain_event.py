"""Unit tests for the :class:`DomainEvent` model."""

from app.events.domain_event import DomainEvent
from app.events.event_type import EventType


def test_domain_event_carries_type_product_and_payload() -> None:
    """A DomainEvent holds its type, product scope and free-form payload."""
    # Act
    event = DomainEvent(
        event_type=EventType.RELEASE_CUT,
        product_id="01AAAAAAAAAAAAAAAAAAAAAAAA",
        data={"release": {"id": "01BBBBBBBBBBBBBBBBBBBBBBBB", "product_version": "5.1.0"}},
    )

    # Assert
    assert event.event_type is EventType.RELEASE_CUT
    assert event.product_id == "01AAAAAAAAAAAAAAAAAAAAAAAA"
    assert event.data["release"]["product_version"] == "5.1.0"


def test_domain_event_coerces_event_type_from_wire_string() -> None:
    """The event_type is coerced from its §6 wire string."""
    # Act
    event = DomainEvent(
        event_type=EventType("version.rolled_back"),
        product_id="01AAAAAAAAAAAAAAAAAAAAAAAA",
        data={"component_id": "01CCCCCCCCCCCCCCCCCCCCCCCC"},
    )

    # Assert
    assert event.event_type is EventType.VERSION_ROLLED_BACK
