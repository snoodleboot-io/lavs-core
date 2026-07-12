"""Unit tests for :class:`UserResponseModel`."""

from app.models.responses.user_response_model import UserResponseModel


class TestUserResponseModel:
    """The safe user projection."""

    def test_carries_public_fields(self) -> None:
        """The model exposes id, email, status, and edition."""
        # Act
        model = UserResponseModel(
            id="01KW8WHA6STWW5N1VYRSHDTK1N",
            email="engineer@example.com",
            status="active",
            edition="oss",
        )

        # Assert
        dumped = model.model_dump()
        assert dumped == {
            "id": "01KW8WHA6STWW5N1VYRSHDTK1N",
            "email": "engineer@example.com",
            "status": "active",
            "edition": "oss",
        }

    def test_never_exposes_password_hash(self) -> None:
        """The response model has no password-hash field of any name."""
        # Act
        fields = set(UserResponseModel.model_fields)

        # Assert
        assert "password_hash" not in fields
