"""Fixed configuration for the browser session cookie.

Per project convention, fixed values live in a named config object rather than
as bare string literals scattered across the login/logout/provider code, so the
cookie's name and security attributes are declared in exactly one place. The
attributes encode the security invariants: ``HttpOnly`` (no JavaScript access),
``Secure`` (HTTPS only), and ``SameSite=Lax`` (CSRF mitigation).
"""

from typing import Literal


class SessionCookie:
    """The name and security attributes of the ``lavs_session`` cookie."""

    NAME: str = "lavs_session"
    PATH: str = "/"
    SAME_SITE: Literal["lax"] = "lax"
    HTTP_ONLY: bool = True
    SECURE: bool = True
