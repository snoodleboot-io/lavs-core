"""Unit tests for :class:`AuthSettings` environment parsing and injection."""

import pytest

from app.auth.auth_mode import AuthMode
from app.auth.auth_settings import AuthSettings

_MODES = "LAVS_AUTH_MODES"
_DOMAINS = "LAVS_ALLOWED_EMAIL_DOMAINS"
_TTL = "LAVS_SESSION_TTL_SECONDS"
_EDITION = "LAVS_EDITION"


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure a clean environment for every case."""
    for name in (
        _MODES,
        _DOMAINS,
        _TTL,
        _EDITION,
    ):
        monkeypatch.delenv(name, raising=False)


class TestModes:
    """``LAVS_AUTH_MODES`` parsing."""

    def test_empty_env_yields_no_modes(self) -> None:
        """No env value means no modes are enabled."""
        # Act / Assert
        assert AuthSettings().modes() == set()

    def test_parses_comma_list(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A comma list is parsed into the AuthMode set (case/space tolerant)."""
        # Arrange
        monkeypatch.setenv(_MODES, " Password , apikey ")

        # Act / Assert
        assert AuthSettings().modes() == {AuthMode.PASSWORD, AuthMode.APIKEY}

    def test_ignores_unknown_modes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Forward-compatible tokens (a mode this build does not ship) are ignored."""
        # Arrange
        monkeypatch.setenv(_MODES, "password,webauthn")

        # Act / Assert
        assert AuthSettings().modes() == {AuthMode.PASSWORD}

    def test_injected_modes_override_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """An explicit modes argument overrides the environment entirely."""
        # Arrange
        monkeypatch.setenv(_MODES, "apikey")

        # Act / Assert
        assert AuthSettings(modes={AuthMode.PASSWORD}).modes() == {AuthMode.PASSWORD}

    def test_password_and_apikey_flags(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The convenience predicates reflect the parsed modes."""
        # Arrange
        monkeypatch.setenv(_MODES, "password")
        settings = AuthSettings()

        # Act / Assert
        assert settings.password_enabled() is True
        assert settings.apikey_mode_enabled() is False


class TestAllowedEmailDomains:
    """``LAVS_ALLOWED_EMAIL_DOMAINS`` parsing."""

    def test_empty_means_allow_all(self) -> None:
        """No env value yields an empty allow-list (allow all)."""
        # Act / Assert
        assert AuthSettings().allowed_email_domains() == ()

    def test_lowercases_and_splits(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Domains are trimmed, split, and lower-cased."""
        # Arrange
        monkeypatch.setenv(_DOMAINS, "Example.com, Acme.IO ")

        # Act / Assert
        assert AuthSettings().allowed_email_domains() == ("example.com", "acme.io")


class TestSessionTtl:
    """``LAVS_SESSION_TTL_SECONDS`` parsing."""

    def test_default_is_one_week(self) -> None:
        """The default TTL is 604800 seconds (7 days)."""
        # Act / Assert
        assert AuthSettings().session_ttl_seconds() == 604800

    def test_parses_env_integer(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A numeric env value overrides the default."""
        # Arrange
        monkeypatch.setenv(_TTL, "3600")

        # Act / Assert
        assert AuthSettings().session_ttl_seconds() == 3600


class TestEdition:
    """``LAVS_EDITION`` parsing."""

    def test_default_is_oss(self) -> None:
        """The default edition is ``oss``."""
        # Act / Assert
        assert AuthSettings().edition() == "oss"

    def test_reads_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """An env value overrides the default edition."""
        # Arrange
        monkeypatch.setenv(_EDITION, "ee")

        # Act / Assert
        assert AuthSettings().edition() == "ee"
