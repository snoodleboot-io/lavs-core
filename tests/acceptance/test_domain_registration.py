"""Acceptance: register the full domain graph end to end (P1 exit criterion).

P1 exit criterion + API_CONTRACT §3: a client can register a product, then a
component under it, then an immutable version under the component -- every
mutation carrying a **JSON body** -- and read the whole graph back via the
timeline composite and the per-component version history.

These tests drive the REAL HTTP endpoints through the FastAPI ``TestClient``.
Until the resource lanes (`/products`, `/components`, `/versions`, timeline) are
merged the endpoints 404, so these acceptance scenarios are expected to be RED.
"""

from fastapi.testclient import TestClient

# Statuses accepted for a successful resource creation. The contract does not
# pin 200 vs 201, so both are treated as success at the acceptance boundary.
_CREATED_OK = (200, 201)


def _create_product(client: TestClient, name: str) -> dict[str, object]:
    """Register a product via ``POST /products`` and return its JSON body.

    Args:
        client: The FastAPI test client.
        name: The product name to register.

    Returns:
        The parsed product response body.
    """
    response = client.post("/products", json={"name": name, "description": "acc-test"})
    assert response.status_code in _CREATED_OK, (
        f"POST /products must create a product; got {response.status_code}: {response.text}"
    )
    return response.json()


def _create_component(
    client: TestClient, product_id: str, name: str, kind: str
) -> dict[str, object]:
    """Register a component via ``POST /components`` and return its JSON body.

    Args:
        client: The FastAPI test client.
        product_id: The parent product id.
        name: The component name.
        kind: The component kind (library/service/ui/cli).

    Returns:
        The parsed component response body.
    """
    response = client.post(
        "/components", json={"product_id": product_id, "name": name, "kind": kind}
    )
    assert response.status_code in _CREATED_OK, (
        f"POST /components must create a component; got {response.status_code}: {response.text}"
    )
    return response.json()


def _create_version(client: TestClient, component_id: str, version: str) -> dict[str, object]:
    """Register a version via ``POST /versions`` and return its JSON body.

    Args:
        client: The FastAPI test client.
        component_id: The parent component id.
        version: The semantic version string.

    Returns:
        The parsed version response body.
    """
    response = client.post("/versions", json={"component_id": component_id, "version": version})
    assert response.status_code in _CREATED_OK, (
        f"POST /versions must create a version; got {response.status_code}: {response.text}"
    )
    return response.json()


class TestDomainRegistration:
    """P1 exit criterion: the product -> component -> version graph registers and reads back."""

    def test_post_product_returns_string_id_and_created_at(self, client: TestClient) -> None:
        """``POST /products`` echoes a string ULID id, the name, and a created_at."""
        # Arrange / Act
        body = _create_product(client, "Aurora Platform")

        # Assert
        assert isinstance(body["id"], str) and body["id"], "product id must be a non-empty string"
        assert body["name"] == "Aurora Platform"
        assert body.get("created_at"), "product must carry a created_at timestamp"

    def test_post_component_links_to_product(self, client: TestClient) -> None:
        """``POST /components`` returns a component bound to its parent product."""
        # Arrange
        product = _create_product(client, "Aurora Platform")

        # Act
        component = _create_component(client, str(product["id"]), "lavs-api", "service")

        # Assert
        assert isinstance(component["id"], str) and component["id"]
        assert component["product_id"] == product["id"]
        assert component["name"] == "lavs-api"
        assert component["kind"] == "service"

    def test_post_version_links_to_component_and_is_active(self, client: TestClient) -> None:
        """``POST /versions`` returns an immutable version with split semver parts."""
        # Arrange
        product = _create_product(client, "Aurora Platform")
        component = _create_component(client, str(product["id"]), "lavs-api", "service")

        # Act
        version = _create_version(client, str(component["id"]), "2.4.0")

        # Assert
        assert isinstance(version["id"], str) and version["id"]
        assert version["component_id"] == component["id"]
        assert (version["major"], version["minor"], version["patch"]) == (2, 4, 0)
        assert version["status"] == "active"
        assert version.get("created_at"), "version must carry a created_at timestamp"

    def test_timeline_returns_full_graph(self, client: TestClient) -> None:
        """``GET /products/{id}/timeline`` returns the product, its components, and versions."""
        # Arrange
        product = _create_product(client, "Aurora Platform")
        component = _create_component(client, str(product["id"]), "lavs-api", "service")
        _create_version(client, str(component["id"]), "1.0.0")
        _create_version(client, str(component["id"]), "1.1.0")

        # Act
        response = client.get(f"/products/{product['id']}/timeline")

        # Assert
        assert response.status_code == 200, (
            f"timeline must return 200; got {response.status_code}: {response.text}"
        )
        body = response.json()
        assert body["product"]["id"] == product["id"]
        components = body["components"]
        assert isinstance(components, list) and len(components) == 1
        graph_component = components[0]
        assert graph_component["id"] == component["id"]
        versions = graph_component["versions"]
        assert isinstance(versions, list) and len(versions) == 2
        recorded = {(v["major"], v["minor"], v["patch"]) for v in versions}
        assert recorded == {(1, 0, 0), (1, 1, 0)}

    def test_component_versions_returns_history(self, client: TestClient) -> None:
        """``GET /components/{id}/versions`` returns the component's version history."""
        # Arrange
        product = _create_product(client, "Aurora Platform")
        component = _create_component(client, str(product["id"]), "lavs-api", "service")
        _create_version(client, str(component["id"]), "1.0.0")
        _create_version(client, str(component["id"]), "2.0.0")

        # Act
        response = client.get(f"/components/{component['id']}/versions")

        # Assert
        assert response.status_code == 200, (
            f"component versions must return 200; got {response.status_code}: {response.text}"
        )
        versions = response.json()
        assert isinstance(versions, list) and len(versions) == 2
        assert all(v["component_id"] == component["id"] for v in versions)
