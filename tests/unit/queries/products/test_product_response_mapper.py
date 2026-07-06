"""Unit tests for :class:`ProductResponseMapper`."""

from datetime import datetime
from unittest import TestCase

from app.queries.products.product_response_mapper import ProductResponseMapper


class TestProductResponseMapper(TestCase):
    """Row-to-model mapping, including the ``created_at`` rendering."""

    def test_maps_row_with_iso_timestamp(self) -> None:
        """A datetime ``created_at`` is rendered as an ISO-8601 string."""
        # Arrange
        row = (
            "01AAAAAAAAAAAAAAAAAAAAAAAA",
            "Aurora",
            "Flagship",
            datetime(2026, 6, 29, 12, 0, 0),
        )

        # Act
        model = ProductResponseMapper.to_model(row)

        # Assert
        assert model.id == "01AAAAAAAAAAAAAAAAAAAAAAAA"
        assert model.name == "Aurora"
        assert model.description == "Flagship"
        assert model.created_at == "2026-06-29T12:00:00"

    def test_maps_null_description_to_none(self) -> None:
        """A ``None`` description is preserved as ``None``."""
        # Arrange
        row = ("01AAAAAAAAAAAAAAAAAAAAAAAA", "Aurora", None, datetime(2026, 6, 29))

        # Act
        model = ProductResponseMapper.to_model(row)

        # Assert
        assert model.description is None
