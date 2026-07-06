"""Integration tests for the ``/products`` routes.

Exercises the full FastAPI stack (routing, dependency-injected managed DuckDB
connection, query execution, and the error-envelope handlers) against a real,
per-test temporary database provided by the ``client`` fixture.
"""

from fastapi.testclient import TestClient


class TestListProducts:
    """``GET /products``."""

    def test_empty_when_no_products(self, client: TestClient) -> None:
        """The list is empty on a fresh database."""
        # Act
        response = client.get("/products")

        # Assert
        assert response.status_code == 200
        assert response.json() == []

    def test_returns_created_products(self, client: TestClient) -> None:
        """Created products appear in the listing."""
        # Arrange
        client.post("/products", json={"name": "Aurora"})
        client.post("/products", json={"name": "Borealis"})

        # Act
        response = client.get("/products")

        # Assert
        assert response.status_code == 200
        names = {product["name"] for product in response.json()}
        assert names == {"Aurora", "Borealis"}


class TestCreateProduct:
    """``POST /products``."""

    def test_creates_product_returns_201(self, client: TestClient) -> None:
        """A valid body creates a product and returns 201 with its fields."""
        # Act
        response = client.post("/products", json={"name": "Aurora", "description": "Flagship"})

        # Assert
        assert response.status_code == 201
        body = response.json()
        assert body["name"] == "Aurora"
        assert body["description"] == "Flagship"
        assert len(body["id"]) == 26
        assert body["created_at"]

    def test_duplicate_name_returns_409(self, client: TestClient) -> None:
        """A repeated name yields a 409 conflict envelope."""
        # Arrange
        client.post("/products", json={"name": "Aurora"})

        # Act
        response = client.post("/products", json={"name": "Aurora"})

        # Assert
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "conflict"

    def test_missing_name_returns_422(self, client: TestClient) -> None:
        """An absent name fails request validation."""
        # Act
        response = client.post("/products", json={"description": "no name"})

        # Assert
        assert response.status_code == 422

    def test_empty_name_returns_422(self, client: TestClient) -> None:
        """An empty name violates the ``MinLen(1)`` constraint."""
        # Act
        response = client.post("/products", json={"name": ""})

        # Assert
        assert response.status_code == 422


class TestGetProduct:
    """``GET /products/{product_id}``."""

    def test_returns_existing_product(self, client: TestClient) -> None:
        """A known id returns the matching product."""
        # Arrange
        created = client.post("/products", json={"name": "Aurora"}).json()

        # Act
        response = client.get(f"/products/{created['id']}")

        # Assert
        assert response.status_code == 200
        assert response.json()["id"] == created["id"]
        assert response.json()["name"] == "Aurora"

    def test_unknown_id_returns_404(self, client: TestClient) -> None:
        """An unknown id yields a 404 not-found envelope."""
        # Act
        response = client.get("/products/01ZZZZZZZZZZZZZZZZZZZZZZZZ")

        # Assert
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"


class TestListProductComponents:
    """``GET /products/{product_id}/components``."""

    def test_unknown_product_returns_404(self, client: TestClient) -> None:
        """Components of an unknown product yield 404, not an empty list."""
        # Act
        response = client.get("/products/01ZZZZZZZZZZZZZZZZZZZZZZZZ/components")

        # Assert
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"

    def test_known_product_without_components_returns_empty(self, client: TestClient) -> None:
        """A known product with no components returns an empty list."""
        # Arrange
        created = client.post("/products", json={"name": "Aurora"}).json()

        # Act
        response = client.get(f"/products/{created['id']}/components")

        # Assert
        assert response.status_code == 200
        assert response.json() == []
