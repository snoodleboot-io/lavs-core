"""Tests for CreateProductModel."""

import pytest
from pydantic import ValidationError

from app.models.requests.create_product_model import CreateProductModel


def test_valid_product_is_accepted() -> None:
    """A non-empty name with an optional description must validate."""
    # Act
    model = CreateProductModel(name="Aurora Platform", description="Flagship")

    # Assert
    assert model.name == "Aurora Platform"
    assert model.description == "Flagship"


def test_description_defaults_to_none() -> None:
    """description must default to None when omitted."""
    # Act
    model = CreateProductModel(name="Aurora Platform")

    # Assert
    assert model.description is None


def test_empty_name_raises_validation_error() -> None:
    """An empty name must raise a validation error."""
    # Act / Assert
    with pytest.raises(ValidationError):
        CreateProductModel(name="")
