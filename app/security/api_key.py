"""API key configuration helpers for the lavs API.

This module exposes the configured API key (if any) and whether API-key
authentication is enabled. Request-time enforcement lives in
:class:`~app.auth.providers.api_key_provider.ApiKeyProvider`, which reads the
header and compares it against the configured key.
"""

from app.security.api_key_settings import ApiKeySettings

# Settings object holding the fixed header/env-var names and providing the
# runtime read of the configured key value.
_settings = ApiKeySettings()

# Names exposed for callers/tests that need the header and environment-variable
# names. These are derived from the settings object rather than defined as bare
# literal constants.
API_KEY_HEADER = _settings.header_name
API_KEY_ENV_VAR = _settings.env_var_name


def get_configured_api_key() -> str | None:
    """Get the configured API key from the environment.

    Returns:
        The API key string if configured, None otherwise.
    """
    return _settings.configured_key()


def is_authentication_enabled() -> bool:
    """Check if authentication is enabled (i.e., an API key is configured).

    Returns:
        True if API key is configured, False otherwise.
    """
    api_key = get_configured_api_key()
    return api_key is not None and api_key != ""
