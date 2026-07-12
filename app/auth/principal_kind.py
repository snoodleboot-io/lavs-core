"""The kind of identity a resolved :class:`~app.auth.principal.Principal` carries."""

from enum import StrEnum


class PrincipalKind(StrEnum):
    """Whether a principal is a human ``user`` or a machine ``service``.

    See ``docs/design/API_CONTRACT.md`` §1 — password/session logins resolve to
    ``user`` principals; API-key (headless) callers resolve to ``service``.
    """

    USER = "user"
    SERVICE = "service"
