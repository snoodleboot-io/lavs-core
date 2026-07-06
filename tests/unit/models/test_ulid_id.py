"""Tests for the ULID id type and helper."""

import pytest
from pydantic import BaseModel, ValidationError

from app.models.types.ulid_id import UlidId, new_ulid


class _UlidHolder(BaseModel):
    """Minimal model exercising the UlidId annotated type."""

    value: UlidId


def test_new_ulid_returns_26_char_string() -> None:
    """new_ulid must return a canonical 26-character ULID string."""
    # Act
    result = new_ulid()

    # Assert
    assert isinstance(result, str)
    assert len(result) == 26


def test_new_ulid_values_are_unique() -> None:
    """Two ULIDs minted in sequence must differ."""
    # Act
    first = new_ulid()
    second = new_ulid()

    # Assert
    assert first != second


def test_valid_ulid_is_accepted() -> None:
    """A freshly minted ULID must validate."""
    # Arrange
    ulid_value = new_ulid()

    # Act
    holder = _UlidHolder(value=ulid_value)

    # Assert
    assert holder.value == ulid_value


@pytest.mark.parametrize(
    "candidate",
    [
        "",
        "not-a-ulid",
        "0123",
        "IIIIIIIIIIIIIIIIIIIIIIIIII",  # 'I' is not in the Crockford alphabet
        "01KW8WHA6STWW5N1VYRSHDTK1",  # 25 chars
        "01KW8WHA6STWW5N1VYRSHDTK1NN",  # 27 chars
    ],
)
def test_invalid_ulid_raises_validation_error(candidate: str) -> None:
    """Malformed ULID strings must raise a validation error."""
    # Act / Assert
    with pytest.raises(ValidationError):
        _UlidHolder(value=candidate)
