"""Unit tests for :class:`AuthSettings` environment parsing and injection."""

import pytest

from app.auth.auth_mode import AuthMode
from app.auth.auth_settings import AuthSettings

_MODES = "LAVS_AUTH_MODES"
_DOMAINS = "LAVS_ALLOWED_EMAIL_DOMAINS"
_TTL = "LAVS_SESSION_TTL_SECONDS"
_EDITION = "LAVS_EDITION"
_STYTCH_PROJECT_ID = "LAVS_STYTCH_PROJECT_ID"
_STYTCH_SECRET = "LAVS_STYTCH_SECRET"
_STYTCH_PUBLIC_TOKEN = "LAVS_STYTCH_PUBLIC_TOKEN"


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure a clean environment for every case."""
    for name in (
        _MODES,
        _DOMAINS,
        _TTL,
        _EDITION,
        _STYTCH_PROJECT_ID,
        _STYTCH_SECRET,
        _STYTCH_PUBLIC_TOKEN,
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
        """Forward-compatible tokens (e.g. stytch) are ignored, not fatal."""
        # Arrange
        monkeypatch.setenv(_MODES, "password,stytch")

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


class TestStytchModeGating:
    """The ``stytch`` token is honoured on EE only (edition × modes matrix)."""

    @pytest.mark.parametrize(
        ("edition", "modes_env", "expected"),
        [
            (None, "stytch", set()),
            ("oss", "stytch", set()),
            ("ee", "stytch", {AuthMode.STYTCH}),
            (None, "password,stytch", {AuthMode.PASSWORD}),
            ("oss", "password,stytch", {AuthMode.PASSWORD}),
            ("ee", "password,stytch", {AuthMode.PASSWORD, AuthMode.STYTCH}),
            ("ee", "stytch,apikey", {AuthMode.STYTCH, AuthMode.APIKEY}),
            ("ee", "password,apikey", {AuthMode.PASSWORD, AuthMode.APIKEY}),
        ],
    )
    def test_edition_gates_the_stytch_token(
        self,
        monkeypatch: pytest.MonkeyPatch,
        edition: str | None,
        modes_env: str,
        expected: set[AuthMode],
    ) -> None:
        """``stytch`` in ``LAVS_AUTH_MODES`` only takes effect when edition is ``ee``."""
        # Arrange
        monkeypatch.setenv(_MODES, modes_env)
        if edition is not None:
            monkeypatch.setenv(_EDITION, edition)

        # Act / Assert
        assert AuthSettings().modes() == expected

    def test_stytch_enabled_true_on_ee(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """``stytch_enabled`` reflects an EE deployment with the mode configured."""
        # Arrange
        monkeypatch.setenv(_MODES, "stytch")
        monkeypatch.setenv(_EDITION, "ee")

        # Act / Assert
        assert AuthSettings().stytch_enabled() is True

    def test_stytch_enabled_false_on_oss(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """On OSS the configured ``stytch`` token stays ignored, exactly as before EE."""
        # Arrange
        monkeypatch.setenv(_MODES, "stytch")

        # Act / Assert
        assert AuthSettings().stytch_enabled() is False

    def test_case_and_space_tolerant_on_ee(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The stytch token parses with the same tolerance as the other modes."""
        # Arrange
        monkeypatch.setenv(_MODES, " Stytch ")
        monkeypatch.setenv(_EDITION, "ee")

        # Act / Assert
        assert AuthSettings().modes() == {AuthMode.STYTCH}


class TestStytchConfig:
    """``LAVS_STYTCH_*`` accessors (project id, secret, public token)."""

    def test_unset_values_are_none(self) -> None:
        """With nothing configured every Stytch accessor returns None."""
        # Arrange
        settings = AuthSettings()

        # Act / Assert
        assert settings.stytch_project_id() is None
        assert settings.stytch_secret() is None
        assert settings.stytch_public_token() is None

    def test_reads_env_values(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Each accessor reads (and trims) its environment variable on demand."""
        # Arrange
        monkeypatch.setenv(_STYTCH_PROJECT_ID, " project-test-123 ")
        monkeypatch.setenv(_STYTCH_SECRET, "secret-test-456")
        monkeypatch.setenv(_STYTCH_PUBLIC_TOKEN, "public-token-789")

        # Act
        settings = AuthSettings()

        # Assert
        assert settings.stytch_project_id() == "project-test-123"
        assert settings.stytch_secret() == "secret-test-456"
        assert settings.stytch_public_token() == "public-token-789"

    def test_blank_env_values_are_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A whitespace-only env value counts as unconfigured."""
        # Arrange
        monkeypatch.setenv(_STYTCH_PROJECT_ID, "   ")
        monkeypatch.setenv(_STYTCH_SECRET, "")

        # Act / Assert
        assert AuthSettings().stytch_project_id() is None
        assert AuthSettings().stytch_secret() is None

    def test_injected_values_override_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Constructor-injected values win over the environment entirely."""
        # Arrange
        monkeypatch.setenv(_STYTCH_PROJECT_ID, "env-project")
        settings = AuthSettings(stytch_project_id="injected-project")

        # Act / Assert
        assert settings.stytch_project_id() == "injected-project"
