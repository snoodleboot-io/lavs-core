"""Unit tests verifying principal authentication is wired onto the routers.

P4 supersedes the bare API-key wiring: every resource router now fixes the
``require_principal`` dependency at the router level (the resolver behind it
decides open-when-unconfigured vs 401-when-configured). These tests assert the
auth contract structurally — that ``require_principal`` is present in each
router's dependency list, and that the public ``/meta`` and credential-
establishing ``/auth`` routers deliberately do **not** carry it — so auth
enforcement is independent of which routes the lanes subsequently add.
"""

import pytest
from fastapi import APIRouter

from app.auth.require_principal import require_principal
from app.routers import (
    auth,
    components,
    events,
    meta,
    products,
    releases,
    timeline,
    versions,
)


def _dependency_callables(router: APIRouter) -> list[object]:
    """Return the callables backing a router's router-level dependencies.

    Args:
        router: The router to inspect.

    Returns:
        The dependency callables declared on the router.
    """
    return [dependant.dependency for dependant in router.dependencies]


@pytest.mark.parametrize(
    "router",
    [
        products.router,
        components.router,
        versions.router,
        timeline.router,
        releases.router,
        events.router,
    ],
)
class TestProtectedRouterWiring:
    """Each resource router must enforce the principal dependency."""

    def test_router_declares_require_principal_dependency(self, router: APIRouter) -> None:
        """The ``require_principal`` dependency is present on the router."""
        # Arrange
        dependencies = _dependency_callables(router)

        # Act / Assert
        assert require_principal in dependencies


@pytest.mark.parametrize("router", [meta.router, auth.router])
class TestPublicRouterWiring:
    """Public / credential-establishing routers must NOT require a principal."""

    def test_router_does_not_require_principal(self, router: APIRouter) -> None:
        """Neither ``/meta`` nor the ``/auth`` shell carries the dependency."""
        # Arrange
        dependencies = _dependency_callables(router)

        # Act / Assert
        assert require_principal not in dependencies


class TestAuthRouterShell:
    """The ``/auth`` router is a mounted, tagged shell for the auth lanes."""

    def test_auth_router_has_prefix(self) -> None:
        """The auth router is mounted under the ``/auth`` prefix."""
        # Act / Assert
        assert auth.router.prefix == "/auth"
