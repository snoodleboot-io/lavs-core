"""The authentication modes selectable via the ``LAVS_AUTH_MODES`` env list."""

from enum import StrEnum


class AuthMode(StrEnum):
    """A deployment-selectable authentication mode.

    Enabled modes are read from the ``LAVS_AUTH_MODES`` comma list (see
    ``docs/design/API_CONTRACT.md`` §1). ``password`` (username/password +
    sessions) is added by the R2 lane; ``apikey`` is the headless ``X-API-Key``
    mode wired here in the foundation. Managed-identity modes live outside core
    in a separate edition and are contributed through the plugin seam, so core
    ships only the two OSS modes.
    """

    PASSWORD = "password"
    APIKEY = "apikey"
