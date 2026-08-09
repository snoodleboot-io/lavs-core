"""FastAPI dependency that resolves the request's principal.

Resource routers depend on this to enforce authentication uniformly. It reads
the application-managed :class:`~app.auth.auth_resolver.AuthResolver` from
``app.state`` (created in the lifespan). When no resolver is present — for
example a bare ``TestClient`` whose lifespan did not run — it falls back to a
resolver built from the current environment, which stays open when nothing is
configured and fail-closed when it is. This mirrors how the DB dependency and
query layer tolerate a lifespan-less ``app.state``.
"""

from typing import Annotated

from fastapi import Depends, Request

from app.auth.auth_resolver import AuthResolver
from app.auth.auth_resolver_factory import AuthResolverFactory
from app.auth.auth_settings import AuthSettings
from app.auth.principal import Principal


def _resolver_for(request: Request) -> AuthResolver:
    """Return the resolver to use for a request.

    Prefers the application-managed resolver on ``app.state``; falls back to an
    environment-built resolver when the app was started without a lifespan.

    Args:
        request: The incoming request.

    Returns:
        The resolver to authenticate with.
    """
    state = request.app.state
    resolver = state.auth_resolver if hasattr(state, "auth_resolver") else None
    if resolver is None:
        return AuthResolverFactory.build_resolver(AuthSettings())
    return resolver


async def require_principal(request: Request) -> Principal:
    """Resolve and return the authenticated principal for the request.

    Args:
        request: The incoming request.

    Returns:
        The resolved :class:`~app.auth.principal.Principal`.

    Raises:
        UnauthorizedError: When auth is configured but no provider authenticates
            the request.
    """
    resolver = _resolver_for(request)
    return await resolver.resolve(request)


PrincipalDep = Annotated[Principal, Depends(require_principal)]
"""Dependency alias injecting the resolved principal into a route."""
