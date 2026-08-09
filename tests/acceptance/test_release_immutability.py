"""Acceptance: a cut release never changes (the core P2 guarantee, API_CONTRACT §5).

Because versions are immutable and a release pins ``version_id``s, a cut release
is a permanent, reproducible statement of the product composition: shipping a new
version or rolling one back afterward must NOT mutate any prior release's frozen
manifest or its server-assigned ``product_version``.

These tests drive the REAL HTTP endpoints through the FastAPI ``TestClient``.
Until the release resource lane is merged the endpoints 404, so these
acceptance scenarios are expected to be RED.
"""

from fastapi.testclient import TestClient

_CREATED_OK = (200, 201)


def _seed_component(client: TestClient) -> tuple[str, str]:
    """Create a product + component and return ``(product_id, component_id)``.

    Args:
        client: The FastAPI test client.

    Returns:
        The created product and component ids.
    """
    product = client.post("/products", json={"name": "Aurora Platform"})
    assert product.status_code in _CREATED_OK, product.text
    product_id = str(product.json()["id"])

    component = client.post(
        "/components", json={"product_id": product_id, "name": "lavs-api", "kind": "service"}
    )
    assert component.status_code in _CREATED_OK, component.text
    return product_id, str(component.json()["id"])


def _create_version(client: TestClient, component_id: str, version: str) -> dict[str, object]:
    """Append an immutable, now-active version to a component.

    Args:
        client: The FastAPI test client.
        component_id: The parent component id.
        version: The semantic version string.

    Returns:
        The parsed version response body.
    """
    response = client.post("/versions", json={"component_id": component_id, "version": version})
    assert response.status_code in _CREATED_OK, response.text
    return response.json()


class TestReleaseImmutability:
    """P2 core guarantee: later version churn never rewrites an existing release manifest."""

    def test_new_version_does_not_alter_prior_release(self, client: TestClient) -> None:
        """Shipping a newer version after a cut leaves that cut's manifest unchanged."""
        # Arrange -- cut a release pinning v1, capture the frozen manifest.
        product_id, component_id = _seed_component(client)
        v1 = _create_version(client, component_id, "1.0.0")
        cut = client.post(f"/products/{product_id}/releases", json={"label": "pinned"})
        assert cut.status_code == 201, cut.text
        release_id = cut.json()["id"]
        frozen = cut.json()

        # Act -- ship a newer active version on the same component.
        v2 = _create_version(client, component_id, "2.0.0")
        assert v2["id"] != v1["id"]

        # Assert -- the prior release still pins v1 and its original product_version.
        refetched = client.get(f"/releases/{release_id}")
        assert refetched.status_code == 200, refetched.text
        body = refetched.json()
        assert body["product_version"] == frozen["product_version"] == "0.1.0"
        assert body["components"] == frozen["components"], "the frozen manifest must not change"
        pinned = next(c for c in body["components"] if str(c["component_id"]) == component_id)
        assert pinned["version_id"] == v1["id"], "the release must still pin the original version"
        assert pinned["version"] == "1.0.0"

    def test_rollback_does_not_alter_prior_release(self, client: TestClient) -> None:
        """Rolling back the active version after a cut leaves that cut's manifest unchanged."""
        # Arrange -- cut a release while v2 is active.
        product_id, component_id = _seed_component(client)
        _create_version(client, component_id, "1.0.0")
        v2 = _create_version(client, component_id, "2.0.0")
        cut = client.post(f"/products/{product_id}/releases", json={})
        assert cut.status_code == 201, cut.text
        release_id = cut.json()["id"]
        frozen_components = cut.json()["components"]

        # Act -- roll the active version back to its predecessor.
        rollback = client.post(f"/versions/{v2['id']}/rollback")
        assert rollback.status_code == 200, rollback.text

        # Assert -- the release still pins v2, the version active at cut time.
        refetched = client.get(f"/releases/{release_id}")
        assert refetched.status_code == 200, refetched.text
        body = refetched.json()
        assert body["components"] == frozen_components, "rollback must not rewrite a cut release"
        pinned = next(c for c in body["components"] if str(c["component_id"]) == component_id)
        assert pinned["version_id"] == v2["id"], (
            "the release must still pin the version cut at cut time"
        )
        assert pinned["version"] == "2.0.0"

    def test_ledger_entry_stable_across_later_versions(self, client: TestClient) -> None:
        """The ledger view of a prior release is stable after later version churn."""
        # Arrange
        product_id, component_id = _seed_component(client)
        _create_version(client, component_id, "1.0.0")
        cut = client.post(f"/products/{product_id}/releases", json={})
        assert cut.status_code == 201, cut.text
        before = next(
            entry
            for entry in client.get(f"/products/{product_id}/releases").json()
            if entry["id"] == cut.json()["id"]
        )

        # Act -- churn versions after the cut.
        _create_version(client, component_id, "1.1.0")

        # Assert
        after = next(
            entry
            for entry in client.get(f"/products/{product_id}/releases").json()
            if entry["id"] == cut.json()["id"]
        )
        assert after["product_version"] == before["product_version"]
        assert after["components"] == before["components"]
