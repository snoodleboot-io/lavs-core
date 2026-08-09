"""Boundary tests for the ``MaxLen`` caps on request models (LAV-51 L-3).

Each cap is exercised at the boundary: a value exactly at the cap validates,
one character over raises ``ValidationError``. The caps are: names/labels 256,
descriptions/notes 4096, email 320 (RFC ceiling), password 128, tokens 256.
"""

import pytest
from pydantic import ValidationError

from app.models.requests.create_component_model import CreateComponentModel
from app.models.requests.create_product_model import CreateProductModel
from app.models.requests.create_version_model import CreateVersionModel
from app.models.requests.cut_release_model import CutReleaseModel
from app.models.requests.login_model import LoginModel
from app.models.requests.verify_model import VerifyModel

ULID = "01KW8WHA6STWW5N1VYRSHDTK1N"


class TestNameCaps:
    """Names and labels are capped at 256 characters."""

    def test_product_name_at_cap_is_accepted(self) -> None:
        """A 256-character product name validates."""
        # Act
        model = CreateProductModel(name="n" * 256)

        # Assert
        assert len(model.name) == 256

    def test_product_name_over_cap_is_rejected(self) -> None:
        """A 257-character product name fails validation."""
        # Act / Assert
        with pytest.raises(ValidationError):
            CreateProductModel(name="n" * 257)

    def test_component_name_over_cap_is_rejected(self) -> None:
        """A 257-character component name fails validation."""
        # Act / Assert
        with pytest.raises(ValidationError):
            CreateComponentModel(product_id=ULID, name="n" * 257, kind="service")

    def test_release_label_at_cap_is_accepted(self) -> None:
        """A 256-character release label validates."""
        # Act
        model = CutReleaseModel(label="l" * 256)

        # Assert
        assert model.label is not None
        assert len(model.label) == 256

    def test_release_label_over_cap_is_rejected(self) -> None:
        """A 257-character release label fails validation."""
        # Act / Assert
        with pytest.raises(ValidationError):
            CutReleaseModel(label="l" * 257)


class TestFreeTextCaps:
    """Descriptions and notes are capped at 4096 characters."""

    def test_product_description_at_cap_is_accepted(self) -> None:
        """A 4096-character description validates."""
        # Act
        model = CreateProductModel(name="Aurora", description="d" * 4096)

        # Assert
        assert model.description is not None
        assert len(model.description) == 4096

    def test_product_description_over_cap_is_rejected(self) -> None:
        """A 4097-character description fails validation."""
        # Act / Assert
        with pytest.raises(ValidationError):
            CreateProductModel(name="Aurora", description="d" * 4097)

    def test_release_notes_at_cap_are_accepted(self) -> None:
        """4096-character release notes validate."""
        # Act
        model = CutReleaseModel(notes="n" * 4096)

        # Assert
        assert model.notes is not None
        assert len(model.notes) == 4096

    def test_release_notes_over_cap_are_rejected(self) -> None:
        """4097-character release notes fail validation."""
        # Act / Assert
        with pytest.raises(ValidationError):
            CutReleaseModel(notes="n" * 4097)


class TestVersionCaps:
    """Version and prerelease strings are capped at 256 characters."""

    def test_version_over_cap_is_rejected(self) -> None:
        """A semver-shaped string longer than 256 characters fails validation."""
        # Arrange: valid semver shape, driven over the cap by its prerelease tag.
        long_version = "1.2.3-" + "a" * 256

        # Act / Assert
        with pytest.raises(ValidationError):
            CreateVersionModel(component_id=ULID, version=long_version)

    def test_prerelease_over_cap_is_rejected(self) -> None:
        """A 257-character prerelease fails validation."""
        # Act / Assert
        with pytest.raises(ValidationError):
            CreateVersionModel(component_id=ULID, version="1.2.3", prerelease="p" * 257)


class TestCredentialCaps:
    """Login email 320, password 128; verification token 256."""

    def test_login_email_at_cap_is_accepted(self) -> None:
        """A 320-character email (RFC ceiling) validates on login."""
        # Arrange
        email = "a" * (320 - len("@example.com")) + "@example.com"

        # Act
        model = LoginModel(email=email, password="p" * 12)

        # Assert
        assert len(model.email) == 320

    def test_login_email_over_cap_is_rejected(self) -> None:
        """A 321-character email fails validation on login."""
        # Act / Assert
        with pytest.raises(ValidationError):
            LoginModel(email="a" * 321, password="p" * 12)

    def test_login_password_at_cap_is_accepted(self) -> None:
        """A 128-character password validates on login."""
        # Act
        model = LoginModel(email="engineer@example.com", password="p" * 128)

        # Assert
        assert len(model.password) == 128

    def test_login_password_over_cap_is_rejected(self) -> None:
        """A 129-character password fails validation on login."""
        # Act / Assert
        with pytest.raises(ValidationError):
            LoginModel(email="engineer@example.com", password="p" * 129)

    def test_verify_token_at_cap_is_accepted(self) -> None:
        """A 256-character verification token validates."""
        # Act
        model = VerifyModel(token="t" * 256)

        # Assert
        assert len(model.token) == 256

    def test_verify_token_over_cap_is_rejected(self) -> None:
        """A 257-character verification token fails validation."""
        # Act / Assert
        with pytest.raises(ValidationError):
            VerifyModel(token="t" * 257)
