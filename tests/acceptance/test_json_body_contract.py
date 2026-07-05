"""Acceptance: mutations take JSON bodies, not query params (P1 exit criterion).

P1 exit criterion (execution plan §1): "mutations move from query-params to JSON
bodies". This suite proves the migration at the HTTP boundary: the same product
payload is **rejected (422)** when supplied as a query string with no body, and
**accepted** when supplied as a JSON body.

These tests drive the REAL HTTP endpoints through the FastAPI ``TestClient``.
Until the products resource lane is merged the endpoint 404s, so these
acceptance scenarios are expected to be RED.
"""

from fastapi.testclient import TestClient

_CREATED_OK = (200, 201)


class TestJsonBodyContract:
    """P1 exit criterion: ``POST /products`` binds a JSON body, not query parameters."""

    def test_query_string_payload_is_rejected(self, client: TestClient) -> None:
        """Supplying the payload as a query string (no body) is rejected with 422."""
        # Arrange / Act -- payload as query params, no JSON body.
        response = client.post("/products", params={"name": "Aurora Platform"})

        # Assert -- the request-body model is required, so binding fails with 422.
        assert response.status_code == 422, (
            "query-string payload (no JSON body) must be rejected with 422; "
            f"got {response.status_code}: {response.text}"
        )
        body = response.json()
        assert isinstance(body, dict) and body.get("error", {}).get("code") == "validation_error", (
            f"rejection must use the validation_error envelope; got {body}"
        )

    def test_json_body_payload_succeeds(self, client: TestClient) -> None:
        """Supplying the same payload as a JSON body creates the product."""
        # Arrange / Act -- identical payload, this time as a JSON body.
        response = client.post("/products", json={"name": "Aurora Platform"})

        # Assert
        assert response.status_code in _CREATED_OK, (
            f"JSON-body payload must create the product; got {response.status_code}: {response.text}"
        )
        body = response.json()
        assert body["name"] == "Aurora Platform"
        assert isinstance(body["id"], str) and body["id"]
