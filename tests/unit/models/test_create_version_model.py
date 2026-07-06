"""Tests for CreateVersionModel."""

import pytest
from pydantic import ValidationError

from app.models.requests.create_version_model import CreateVersionModel
from app.models.types.ulid_id import new_ulid


@pytest.mark.parametrize(
    "version",
    ["1.2.3", "1.2.3-rc.1", "0.0.0", "10.20.30", "1.2.3-alpha-1"],
)
def test_valid_versions_are_accepted(version: str) -> None:
    """Valid semantic versions must validate."""
    # Act
    model = CreateVersionModel(component_id=new_ulid(), version=version)

    # Assert
    assert model.version == version


@pytest.mark.parametrize(
    "version",
    ["1.2.3.4", "1.2.3abc", "1.2", "x.y.z", "", "v1.2.3", "1.2.3-"],
)
def test_invalid_versions_raise_validation_error(version: str) -> None:
    """Malformed versions must raise a validation error."""
    # Act / Assert
    with pytest.raises(ValidationError):
        CreateVersionModel(component_id=new_ulid(), version=version)


@pytest.mark.parametrize(
    ("version", "expected_major", "expected_minor", "expected_patch"),
    [
        ("1.2.3", 1, 2, 3),
        ("1.2.3-rc.1", 1, 2, 3),
        ("10.20.30", 10, 20, 30),
    ],
)
def test_version_components_are_parsed(
    version: str,
    expected_major: int,
    expected_minor: int,
    expected_patch: int,
) -> None:
    """Major, minor and patch must be derived from the version."""
    # Act
    model = CreateVersionModel(component_id=new_ulid(), version=version)

    # Assert
    assert model.major == expected_major
    assert model.minor == expected_minor
    assert model.patch == expected_patch


def test_invalid_component_id_raises_validation_error() -> None:
    """A non-ULID component_id must raise a validation error."""
    # Act / Assert
    with pytest.raises(ValidationError):
        CreateVersionModel(component_id="not-a-ulid", version="1.0.0")


def test_prerelease_defaults_to_none() -> None:
    """prerelease must default to None when omitted."""
    # Act
    model = CreateVersionModel(component_id=new_ulid(), version="1.0.0")

    # Assert
    assert model.prerelease is None
