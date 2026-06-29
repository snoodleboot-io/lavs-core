"""API key authentication configuration.

Holds the fixed configuration for API-key authentication (the request header
name and the environment-variable name that carries the configured key) plus a
runtime read of the configured key value from the environment.

Per project conventions, fixed configuration is expressed through a settings
class rather than bare module-level constants. The key value itself is read
from the environment at call time so it can be changed at runtime without
re-importing the module.
"""

import os


class ApiKeySettings:
    """Configuration for API-key authentication.

    The fixed names (request header and environment variable) are held as
    instance attributes initialized from class-level defaults rather than as
    module-level constants. The configured key value is read from the
    environment on demand via :meth:`configured_key`.
    """

    _DEFAULT_HEADER_NAME: str = "X-API-Key"
    _DEFAULT_ENV_VAR_NAME: str = "LAVS_API_KEY"

    def __init__(
        self,
        header_name: str | None = None,
        env_var_name: str | None = None,
    ) -> None:
        """Initialize API-key settings.

        Args:
            header_name: Request header carrying the API key. Defaults to the
                fixed ``X-API-Key`` name when not provided.
            env_var_name: Environment variable carrying the configured key.
                Defaults to the fixed ``LAVS_API_KEY`` name when not provided.
        """
        self._header_name: str = header_name or self._DEFAULT_HEADER_NAME
        self._env_var_name: str = env_var_name or self._DEFAULT_ENV_VAR_NAME

    @property
    def header_name(self) -> str:
        """Name of the request header that carries the API key."""
        return self._header_name

    @property
    def env_var_name(self) -> str:
        """Name of the environment variable that carries the configured key."""
        return self._env_var_name

    def configured_key(self) -> str | None:
        """Read the configured API key from the environment.

        Returns:
            The configured key string if the environment variable is set,
            otherwise ``None``.
        """
        return os.environ.get(self._env_var_name)
