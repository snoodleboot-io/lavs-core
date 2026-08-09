"""Unit tests for :class:`RateLimitSettings`."""

import pytest

from app.security.rate_limit_settings import RateLimitSettings


class TestDefaults:
    """Default posture with a clean environment."""

    def test_limiting_is_disabled_by_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """With no environment set the limiter is off (limit 0)."""
        # Arrange
        monkeypatch.delenv("LAVS_AUTH_RATE_LIMIT", raising=False)
        monkeypatch.delenv("LAVS_AUTH_RATE_WINDOW_SECONDS", raising=False)
        settings = RateLimitSettings()

        # Act / Assert
        assert settings.limit() == 0
        assert settings.window_seconds() == 60
        assert settings.enabled() is False

    def test_trust_forwarded_for_defaults_off(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """``X-Forwarded-For`` is not trusted unless explicitly enabled."""
        # Arrange
        monkeypatch.delenv("LAVS_AUTH_RATE_TRUST_FORWARDED_FOR", raising=False)
        settings = RateLimitSettings()

        # Act / Assert
        assert settings.trust_forwarded_for() is False

    def test_max_tracked_clients_has_a_fixed_default(self) -> None:
        """The bucket cap defaults to a fixed bound."""
        # Arrange
        settings = RateLimitSettings()

        # Act / Assert
        assert settings.max_tracked_clients() == 1024


class TestEnvironmentReads:
    """Values resolve from the ``LAVS_AUTH_RATE_*`` environment on demand."""

    def test_limit_and_window_read_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Positive env values enable limiting with those numbers."""
        # Arrange
        monkeypatch.setenv("LAVS_AUTH_RATE_LIMIT", "20")
        monkeypatch.setenv("LAVS_AUTH_RATE_WINDOW_SECONDS", "30")
        settings = RateLimitSettings()

        # Act / Assert
        assert settings.limit() == 20
        assert settings.window_seconds() == 30
        assert settings.enabled() is True

    def test_zero_limit_disables(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """An explicit ``0`` limit disables limiting."""
        # Arrange
        monkeypatch.setenv("LAVS_AUTH_RATE_LIMIT", "0")
        settings = RateLimitSettings()

        # Act / Assert
        assert settings.enabled() is False

    def test_blank_values_fall_back_to_defaults(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Whitespace-only env values behave as unset."""
        # Arrange
        monkeypatch.setenv("LAVS_AUTH_RATE_LIMIT", "   ")
        monkeypatch.setenv("LAVS_AUTH_RATE_WINDOW_SECONDS", " ")
        settings = RateLimitSettings()

        # Act / Assert
        assert settings.limit() == 0
        assert settings.window_seconds() == 60

    @pytest.mark.parametrize("raw", ["1", "true", "TRUE", "yes", "on"])
    def test_truthy_trust_flag_values(self, monkeypatch: pytest.MonkeyPatch, raw: str) -> None:
        """Common truthy spellings enable X-Forwarded-For trust."""
        # Arrange
        monkeypatch.setenv("LAVS_AUTH_RATE_TRUST_FORWARDED_FOR", raw)
        settings = RateLimitSettings()

        # Act / Assert
        assert settings.trust_forwarded_for() is True

    @pytest.mark.parametrize("raw", ["0", "false", "off", "nope", ""])
    def test_falsy_trust_flag_values(self, monkeypatch: pytest.MonkeyPatch, raw: str) -> None:
        """Anything else keeps the trust flag off."""
        # Arrange
        monkeypatch.setenv("LAVS_AUTH_RATE_TRUST_FORWARDED_FOR", raw)
        settings = RateLimitSettings()

        # Act / Assert
        assert settings.trust_forwarded_for() is False


class TestConstructorOverrides:
    """Injected values override the environment entirely."""

    def test_injected_values_win_over_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Constructor arguments shadow any environment configuration."""
        # Arrange
        monkeypatch.setenv("LAVS_AUTH_RATE_LIMIT", "5")
        monkeypatch.setenv("LAVS_AUTH_RATE_WINDOW_SECONDS", "10")
        monkeypatch.setenv("LAVS_AUTH_RATE_TRUST_FORWARDED_FOR", "true")
        settings = RateLimitSettings(
            limit=2,
            window_seconds=99,
            trust_forwarded_for=False,
            max_tracked_clients=7,
        )

        # Act / Assert
        assert settings.limit() == 2
        assert settings.window_seconds() == 99
        assert settings.trust_forwarded_for() is False
        assert settings.max_tracked_clients() == 7

    def test_zero_window_disables(self) -> None:
        """A zero window disables limiting even with a positive limit."""
        # Arrange
        settings = RateLimitSettings(limit=5, window_seconds=0)

        # Act / Assert
        assert settings.enabled() is False
