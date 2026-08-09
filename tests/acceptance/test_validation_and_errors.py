"""Acceptance: validation failures + the uniform error envelope (P1 exit criterion).

P1 exit criterion + API_CONTRACT §3: every failure serializes to the single
shape ``{"error": {"code", "message", "details"}}``. This suite pins the status
code and the stable machine-readable ``code`` for each failure mode:

* non-semver ``version``          -> 422 ``validation_error``
* unknown ``component_id``        -> 404 ``not_found``
* unknown product on timeline     -> 404 ``not_found``
* duplicate product ``name``      -> 409 ``conflict``

These tests drive the REAL HTTP endpoints through the FastAPI ``TestClient``.
Until the resource lanes are merged the endpoints 404 for the wrong reason
(route missing, not domain 404), so most of these scenarios are expected to be
RED until the lanes land.
"""

from fastapi.testclient import TestClient

from app.models.types.ulid_id import new_ulid

_CREATED_OK = (200, 201)


def _assert_error_envelope(payload: object, expected_code: str) -> None:
    """Assert the response body is the uniform error envelope with the given code.

    Args:
        payload: The parsed JSON response body.
        expected_code: The stable machine-readable code that must be present.
    """
    assert isinstance(payload, dict), f"error body must be a JSON object; got {type(payload)}"
    assert "error" in payload, f"error body must be wrapped in an 'error' key; got {payload}"
    error = payload["error"]
    assert isinstance(error, dict), "the 'error' value must be an object"
    assert set(error) >= {"code", "message", "details"}, (
        f"error object must carry code/message/details; got keys {set(error)}"
    )
    assert error["code"] == expected_code, (
        f"expected error code {expected_code!r}; got {error['code']!r}"
    )
    assert isinstance(error["message"], str) and error["message"]
    assert isinstance(error["details"], dict)


def _create_component(client: TestClient) -> str:
    """Create a product + component and return the component id.

    Args:
        client: The FastAPI test client.

    Returns:
        The created component's id.
    """
    product = client.post("/products", json={"name": "Aurora Platform"})
    assert product.status_code in _CREATED_OK, product.text
    component = client.post(
        "/components",
        json={"product_id": product.json()["id"], "name": "lavs-api", "kind": "service"},
    )
    assert component.status_code in _CREATED_OK, component.text
    return str(component.json()["id"])


class TestValidationAndErrors:
    """P1 exit criterion: uniform error envelope across validation and domain failures."""

    def test_non_semver_version_returns_422_validation_error(self, client: TestClient) -> None:
        """A non-semantic ``version`` string is rejected with a 422 validation envelope."""
        # Arrange
        component_id = _create_component(client)

        # Act
        response = client.post(
            "/versions", json={"component_id": component_id, "version": "not-semver"}
        )

        # Assert
        assert response.status_code == 422, (
            f"non-semver version must return 422; got {response.status_code}: {response.text}"
        )
        _assert_error_envelope(response.json(), "validation_error")

    def test_unknown_component_on_create_version_returns_404(self, client: TestClient) -> None:
        """Creating a version for an unknown (but well-formed) component id yields 404."""
        # Arrange
        missing_component_id = new_ulid()

        # Act
        response = client.post(
            "/versions", json={"component_id": missing_component_id, "version": "1.0.0"}
        )

        # Assert
        assert response.status_code == 404, (
            f"unknown component_id must return 404; got {response.status_code}: {response.text}"
        )
        _assert_error_envelope(response.json(), "not_found")

    def test_unknown_product_on_timeline_returns_404(self, client: TestClient) -> None:
        """Requesting the timeline of an unknown product id yields a 404 envelope."""
        # Arrange
        missing_product_id = new_ulid()

        # Act
        response = client.get(f"/products/{missing_product_id}/timeline")

        # Assert
        assert response.status_code == 404, (
            f"unknown product timeline must return 404; got {response.status_code}: {response.text}"
        )
        _assert_error_envelope(response.json(), "not_found")

    def test_duplicate_product_name_returns_409_conflict(self, client: TestClient) -> None:
        """Registering a product name that already exists yields a 409 conflict envelope."""
        # Arrange
        first = client.post("/products", json={"name": "Aurora Platform"})
        assert first.status_code in _CREATED_OK, first.text

        # Act
        duplicate = client.post("/products", json={"name": "Aurora Platform"})

        # Assert
        assert duplicate.status_code == 409, (
            f"duplicate product name must return 409; got {duplicate.status_code}: {duplicate.text}"
        )
        _assert_error_envelope(duplicate.json(), "conflict")
