"""Tests for the API key configuration helpers."""

import pytest

from app.security.api_key import (
    API_KEY_ENV_VAR,
    get_configured_api_key,
    is_authentication_enabled,
)


class TestGetConfiguredApiKey:
    """Tests for get_configured_api_key function."""

    def test_returns_none_when_env_var_not_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that None is returned when LAVS_API_KEY is not set."""
        monkeypatch.delenv(API_KEY_ENV_VAR, raising=False)
        result = get_configured_api_key()
        assert result is None

    def test_returns_api_key_when_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that the API key is returned when set."""
        monkeypatch.setenv(API_KEY_ENV_VAR, "test-api-key")
        result = get_configured_api_key()
        assert result == "test-api-key"

    def test_returns_empty_string_when_env_var_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that empty string is returned when env var is empty."""
        monkeypatch.setenv(API_KEY_ENV_VAR, "")
        result = get_configured_api_key()
        assert result == ""


class TestIsAuthenticationEnabled:
    """Tests for is_authentication_enabled function."""

    def test_returns_false_when_env_var_not_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that False is returned when LAVS_API_KEY is not set."""
        monkeypatch.delenv(API_KEY_ENV_VAR, raising=False)
        assert is_authentication_enabled() is False

    def test_returns_true_when_api_key_is_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that True is returned when API key is configured."""
        monkeypatch.setenv(API_KEY_ENV_VAR, "test-api-key")
        assert is_authentication_enabled() is True

    def test_returns_false_when_api_key_is_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that False is returned when API key is empty string."""
        monkeypatch.setenv(API_KEY_ENV_VAR, "")
        assert is_authentication_enabled() is False
