"""Unit tests for :class:`Principal`."""

from app.auth.principal import Principal
from app.auth.principal_kind import PrincipalKind


class TestPrincipal:
    """The resolved-caller model."""

    def test_user_principal_carries_all_fields(self) -> None:
        """A user principal round-trips kind, id, email, and edition."""
        # Arrange / Act
        principal = Principal(
            kind=PrincipalKind.USER, id="u1", email="engineer@example.com", edition="oss"
        )

        # Assert
        assert principal.kind is PrincipalKind.USER
        assert principal.id == "u1"
        assert principal.email == "engineer@example.com"
        assert principal.edition == "oss"

    def test_email_is_optional(self) -> None:
        """A service principal may omit the email."""
        # Act
        principal = Principal(kind=PrincipalKind.SERVICE, id="anonymous", edition="oss")

        # Assert
        assert principal.email is None
