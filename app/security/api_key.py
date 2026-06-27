"""API key authentication module for lavs API.

This module provides API key-based authentication for protecting routes.
It supports optional authentication - when no API key is configured,
all requests are allowed through.
"""

import logging
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

from app.security.api_key_settings import ApiKeySettings

logger = logging.getLogger("lavs-api")

# Settings object holding the fixed header/env-var names and providing the
# runtime read of the configured key value.
_settings = ApiKeySettings()

# Names exposed for the FastAPI dependency and for callers/tests that need the
# header and environment-variable names. These are derived from the settings
# object rather than defined as bare literal constants.
API_KEY_HEADER = _settings.header_name
API_KEY_ENV_VAR = _settings.env_var_name

# Header dependency for FastAPI
api_key_header = APIKeyHeader(name=API_KEY_HEADER, auto_error=False)


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


async def get_api_key(api_key: Annotated[str | None, Depends(api_key_header)] = None) -> str:
    """Validate the API key from the request header.

    This dependency can be used to protect routes. When authentication
    is disabled (no API key configured), any request is allowed through.

    Args:
        api_key: The API key from the request header, provided by FastAPI
                 dependency injection.

    Returns:
        The validated API key, or empty string if auth is disabled.

    Raises:
        HTTPException: If authentication is enabled and the provided
                       API key is invalid or missing.
    """
    # If no API key is configured, allow all requests (optional auth)
    if not is_authentication_enabled():
        logger.debug("Authentication disabled - allowing request")
        return api_key if api_key is not None else ""

    # Authentication is enabled - validate the API key
    configured_key = get_configured_api_key()

    if api_key is None:
        logger.warning("API key missing in request")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"API key is required. Provide it in the {API_KEY_HEADER} header.",
        )

    if api_key != configured_key:
        logger.warning("Invalid API key provided")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )

    logger.debug("API key validated successfully")
    return api_key


# Type alias for dependency injection
ApiKeyDep = Annotated[str, Depends(get_api_key)]
