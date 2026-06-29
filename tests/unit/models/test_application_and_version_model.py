import pytest
from pydantic import ValidationError

from app.models.requests.application_and_version_model import (
    ApplicationAndVersionNameModel,
)


@pytest.mark.parametrize(
    "version",
    [
        "1.2.3",
        "1.2.3-rc.1",
        "0.0.0",
        "10.20.30",
        "1.2.3-alpha-1",
    ],
)
def test_valid_versions_are_accepted(version: str) -> None:
    """Valid semantic versions must pass validation."""
    model = ApplicationAndVersionNameModel(product_name="Sample", version=version)

    assert model.version == version


@pytest.mark.parametrize(
    "version",
    [
        "1.2.3.4",
        "1.2.3abc",
        "1.2",
        "x.y.z",
        "",
        "v1.2.3",
        "1.2.3-",
    ],
)
def test_invalid_versions_raise_validation_error(version: str) -> None:
    """Malformed versions must raise a validation error."""
    with pytest.raises(ValidationError):
        ApplicationAndVersionNameModel(product_name="Sample", version=version)


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
    """Major, minor, and patch components must be derived from the version."""
    model = ApplicationAndVersionNameModel(product_name="Sample", version=version)

    assert model.major == expected_major
    assert model.minor == expected_minor
    assert model.patch == expected_patch
