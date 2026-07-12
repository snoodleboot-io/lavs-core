"""The resolved caller identity injected into every protected route."""

from pydantic import BaseModel

from app.auth.principal_kind import PrincipalKind


class Principal(BaseModel):
    """The authenticated caller, as resolved by the auth spine.

    Mirrors the contract's ``Principal = {kind, id, email?, edition}`` (see
    ``docs/design/API_CONTRACT.md`` §1). Resource routes depend on a resolved
    principal without caring which provider produced it, which is exactly what
    lets new providers (password/session, Stytch) be added without touching the
    routes.
    """

    kind: PrincipalKind
    id: str
    email: str | None = None
    edition: str
