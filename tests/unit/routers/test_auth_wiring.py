"""Unit tests verifying API-key authentication is wired onto the data routers.

The P1 resource routers (products, components, versions, timeline) are created
as shells with the API-key dependency fixed at the router level; the resource
lanes add the routes. These tests assert the auth contract structurally — that
``get_api_key`` is present in each router's dependency list — so auth remains
enforced no matter which routes the lanes subsequently add.
"""

import pytest
from fastapi import APIRouter

from app.routers import components, products, timeline, versions
from app.security.api_key import get_api_key


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
    [products.router, components.router, versions.router, timeline.router],
)
class TestAuthWiring:
    """Each P1 resource router must enforce the API-key dependency."""

    def test_router_declares_api_key_dependency(self, router: APIRouter) -> None:
        """The ``get_api_key`` dependency is present on the router."""
        # Arrange
        dependencies = _dependency_callables(router)

        # Act / Assert
        assert get_api_key in dependencies

    def test_router_has_expected_prefix(self, router: APIRouter) -> None:
        """The router is mounted under a non-empty resource prefix."""
        # Arrange
        prefix = router.prefix

        # Act / Assert
        assert prefix.startswith("/")
        assert len(prefix) > 1
