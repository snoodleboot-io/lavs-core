"""Unit tests for :class:`SignupModel` input validation and normalisation."""

from unittest import TestCase

from pydantic import ValidationError

from app.auth.signup.signup_policy import SignupPolicy
from app.models.requests.signup_model import SignupModel


class TestSignupModel(TestCase):
    """Email normalisation and password-strength validation."""

    def _valid_password(self) -> str:
        return "a" * SignupPolicy.MIN_PASSWORD_LENGTH

    def test_email_is_lowercased_and_trimmed(self) -> None:
        """A mixed-case, padded email is normalised to lower-case and trimmed."""
        # Arrange / Act
        model = SignupModel(email="  Engineer@Example.COM  ", password=self._valid_password())

        # Assert
        assert model.email == "engineer@example.com"

    def test_malformed_email_is_rejected(self) -> None:
        """An address without a domain fails validation."""
        # Act / Assert
        with self.assertRaises(ValidationError):
            SignupModel(email="not-an-email", password=self._valid_password())

    def test_short_password_is_rejected(self) -> None:
        """A password below the policy minimum fails validation."""
        # Arrange
        short = "a" * (SignupPolicy.MIN_PASSWORD_LENGTH - 1)

        # Act / Assert
        with self.assertRaises(ValidationError):
            SignupModel(email="engineer@example.com", password=short)

    def test_minimum_length_password_is_accepted(self) -> None:
        """A password exactly at the minimum length is accepted."""
        # Act
        model = SignupModel(email="engineer@example.com", password=self._valid_password())

        # Assert
        assert len(model.password) == SignupPolicy.MIN_PASSWORD_LENGTH
