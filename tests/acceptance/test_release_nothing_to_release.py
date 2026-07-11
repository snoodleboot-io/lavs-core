"""Acceptance: cutting a product with nothing active is a 409 conflict (P2 decision).

A release is a snapshot of each component's ``active`` version. When a product
has no active versions to snapshot -- because it has components but none carry a
version, or because it has no components at all -- there is nothing to release, so
the cut is rejected with **409 conflict** rather than producing an empty manifest.

These tests drive the REAL HTTP endpoints through the FastAPI ``TestClient``.
Until the release resource lane is merged the endpoint 404s, so these
acceptance scenarios are expected to be RED.
"""

from fastapi.testclient import TestClient

_CREATED_OK = (200, 201)


def _create_product(client: TestClient) -> str:
    """Register a product and return its id.

    Args:
        client: The FastAPI test client.

    Returns:
        The created product's id.
    """
    response = client.post("/products", json={"name": "Aurora Platform"})
    assert response.status_code in _CREATED_OK, response.text
    return str(response.json()["id"])


class TestNothingToRelease:
    """P2 decision: no active version to snapshot -> the cut is a 409 conflict."""

    def test_cut_with_no_components_is_conflict(self, client: TestClient) -> None:
        """A product with no components has nothing to release -> 409."""
        # Arrange
        product_id = _create_product(client)

        # Act
        response = client.post(f"/products/{product_id}/releases", json={})

        # Assert
        assert response.status_code == 409, (
            f"cutting an empty product must conflict; got {response.status_code}: {response.text}"
        )

    def test_cut_with_components_but_no_versions_is_conflict(self, client: TestClient) -> None:
        """A product whose components carry no active version -> 409."""
        # Arrange
        product_id = _create_product(client)
        component = client.post(
            "/components", json={"product_id": product_id, "name": "lavs-api", "kind": "service"}
        )
        assert component.status_code in _CREATED_OK, component.text

        # Act
        response = client.post(f"/products/{product_id}/releases", json={})

        # Assert
        assert response.status_code == 409, (
            f"cutting with no active versions must conflict; got {response.status_code}: {response.text}"
        )

    def test_conflict_does_not_create_a_release(self, client: TestClient) -> None:
        """A rejected cut leaves the ledger empty -- no phantom release is persisted."""
        # Arrange
        product_id = _create_product(client)
        client.post(
            "/components", json={"product_id": product_id, "name": "lavs-api", "kind": "service"}
        )

        # Act
        conflict = client.post(f"/products/{product_id}/releases", json={})

        # Assert
        assert conflict.status_code == 409, conflict.text
        ledger = client.get(f"/products/{product_id}/releases")
        assert ledger.status_code == 200, ledger.text
        assert ledger.json() == [], "a conflicting cut must not persist a release"
