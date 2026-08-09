"""Unit tests for the pure product-version derivation helpers."""

import pytest

from app.domain.product_version import bump_minor, next_product_version


def test_bump_minor_increments_minor_and_resets_patch() -> None:
    """A minor bump raises minor by one and zeroes the patch."""
    # Act
    result = bump_minor("5.1.3")

    # Assert
    assert result == "5.2.0"


def test_bump_minor_from_zero() -> None:
    """Bumping the default base yields the first minor version."""
    # Act
    result = bump_minor("0.0.0")

    # Assert
    assert result == "0.1.0"


def test_bump_minor_drops_prerelease_suffix() -> None:
    """A prerelease suffix is dropped by the minor bump."""
    # Act
    result = bump_minor("2.4.0-rc.1")

    # Assert
    assert result == "2.5.0"


def test_bump_minor_rejects_non_semver() -> None:
    """A non ``major.minor.patch`` string is rejected."""
    # Act / Assert
    with pytest.raises(ValueError):
        bump_minor("1.2")


def test_bump_minor_rejects_non_integer_component() -> None:
    """A non-integer component is rejected."""
    # Act / Assert
    with pytest.raises(ValueError):
        bump_minor("1.x.0")


def test_bump_minor_rejects_negative_component() -> None:
    """A negative component is rejected."""
    # Act / Assert
    with pytest.raises(ValueError):
        bump_minor("1.-2.0")


def test_next_product_version_uses_base_when_no_releases() -> None:
    """With no prior release the base version is the current version bumped."""
    # Act
    result = next_product_version(latest_release_version=None, base_version="0.0.0")

    # Assert
    assert result == "0.1.0"


def test_next_product_version_bumps_configured_non_zero_base() -> None:
    """A non-default base is honoured on the first cut."""
    # Act
    result = next_product_version(latest_release_version=None, base_version="5.0.0")

    # Assert
    assert result == "5.1.0"


def test_next_product_version_bumps_latest_release() -> None:
    """With a prior release the latest release version is bumped, not the base."""
    # Act
    result = next_product_version(latest_release_version="5.3.2", base_version="0.0.0")

    # Assert
    assert result == "5.4.0"
