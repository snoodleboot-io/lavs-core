"""Tests for CreateComponentModel."""

import pytest
from pydantic import ValidationError

from app.models.enums.component_kind import ComponentKind
from app.models.requests.create_component_model import CreateComponentModel
from app.models.types.ulid_id import new_ulid


def test_valid_component_is_accepted() -> None:
    """A valid product_id, name and kind must validate."""
    # Arrange
    product_id = new_ulid()

    # Act
    model = CreateComponentModel(product_id=product_id, name="lavs-api", kind=ComponentKind.SERVICE)

    # Assert
    assert model.product_id == product_id
    assert model.kind is ComponentKind.SERVICE


def test_kind_accepts_string_value() -> None:
    """The kind field must coerce a valid string into the enum."""
    # Act
    model = CreateComponentModel(product_id=new_ulid(), name="ui-app", kind="ui")

    # Assert
    assert model.kind is ComponentKind.UI


def test_invalid_kind_raises_validation_error() -> None:
    """An unknown kind must raise a validation error."""
    # Act / Assert
    with pytest.raises(ValidationError):
        CreateComponentModel(product_id=new_ulid(), name="x", kind="firmware")


def test_invalid_product_id_raises_validation_error() -> None:
    """A non-ULID product_id must raise a validation error."""
    # Act / Assert
    with pytest.raises(ValidationError):
        CreateComponentModel(product_id="not-a-ulid", name="x", kind=ComponentKind.CLI)


def test_empty_name_raises_validation_error() -> None:
    """An empty name must raise a validation error."""
    # Act / Assert
    with pytest.raises(ValidationError):
        CreateComponentModel(product_id=new_ulid(), name="", kind=ComponentKind.LIBRARY)
