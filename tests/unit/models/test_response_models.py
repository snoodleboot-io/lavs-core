"""Tests for the response models."""

from app.models.enums.component_kind import ComponentKind
from app.models.enums.version_status import VersionStatus
from app.models.responses.component_response_model import ComponentResponseModel
from app.models.responses.component_with_versions_response_model import (
    ComponentWithVersionsResponseModel,
)
from app.models.responses.product_response_model import ProductResponseModel
from app.models.responses.timeline_response_model import TimelineResponseModel
from app.models.responses.version_response_model import VersionResponseModel


def _version() -> VersionResponseModel:
    """Build a representative version response."""
    return VersionResponseModel(
        id="01KW8WHA6STWW5N1VYRSHDTK1N",
        component_id="01KW8WHA6STWW5N1VYRSHDTK1P",
        major=2,
        minor=4,
        patch=0,
        prerelease=None,
        status=VersionStatus.ACTIVE,
        created_at="2026-06-29T12:00:00Z",
    )


def test_product_response_model_round_trips() -> None:
    """ProductResponseModel must carry its contract fields."""
    # Act
    model = ProductResponseModel(
        id="01KW8WHA6STWW5N1VYRSHDTK1N",
        name="Aurora Platform",
        description=None,
        created_at="2026-06-29T12:00:00Z",
    )

    # Assert
    assert model.description is None
    assert model.name == "Aurora Platform"


def test_component_response_model_holds_kind_enum() -> None:
    """ComponentResponseModel must coerce kind into the enum."""
    # Act
    model = ComponentResponseModel(
        id="01KW8WHA6STWW5N1VYRSHDTK1N",
        product_id="01KW8WHA6STWW5N1VYRSHDTK1P",
        name="lavs-api",
        kind="service",
    )

    # Assert
    assert model.kind is ComponentKind.SERVICE


def test_version_response_model_holds_status_enum() -> None:
    """VersionResponseModel must coerce status into the enum."""
    # Act
    model = _version()

    # Assert
    assert model.status is VersionStatus.ACTIVE


def test_timeline_response_model_nests_components_and_versions() -> None:
    """TimelineResponseModel must nest components and their versions."""
    # Arrange
    product = ProductResponseModel(
        id="01KW8WHA6STWW5N1VYRSHDTK1N",
        name="Aurora Platform",
        description=None,
        created_at="2026-06-29T12:00:00Z",
    )
    component = ComponentWithVersionsResponseModel(
        id="01KW8WHA6STWW5N1VYRSHDTK1P",
        product_id="01KW8WHA6STWW5N1VYRSHDTK1N",
        name="lavs-api",
        kind=ComponentKind.SERVICE,
        versions=[_version()],
    )

    # Act
    timeline = TimelineResponseModel(product=product, components=[component])

    # Assert
    assert timeline.components[0].versions[0].major == 2
    assert timeline.product.name == "Aurora Platform"
