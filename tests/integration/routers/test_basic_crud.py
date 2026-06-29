"""Integration tests for the basic_crud router.

These tests verify the CRUD operations via the API endpoints.
"""

from fastapi.testclient import TestClient


class TestBasicCrudRouter:
    """Test suite for basic_crud API endpoints."""

    def test_read_all_empty(self, client: TestClient) -> None:
        """Test GET /crud/read_all returns empty list when no data exists.

        When there are no versions in the database, the endpoint should
        return an empty list.
        """
        response = client.get("/crud/read_all?product_name=test")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_read_all_with_data(self, client: TestClient) -> None:
        """Test GET /crud/read_all returns data after creating versions.

        First creates versions via the versions endpoint, then verifies
        they are returned by the read_all endpoint.
        """
        # Create a version
        create_response = client.post("/versions/?product_name=crudtest&version=1.0.0")
        assert create_response.status_code == 200

        # Create another version
        create_response2 = client.post("/versions/?product_name=crudtest&version=2.0.0")
        assert create_response2.status_code == 200

        # Read all versions
        response = client.get("/crud/read_all?product_name=crudtest")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2

        # Verify the versions are returned in descending order (latest first)
        assert data[0]["product_name"] == "crudtest"
        assert data[0]["major"] == 2
        assert data[0]["minor"] == 0
        assert data[0]["patch"] == 0
        assert data[1]["major"] == 1
        assert data[1]["minor"] == 0
        assert data[1]["patch"] == 0

    def test_read_all_filtered_by_product_name(self, client: TestClient) -> None:
        """Test GET /crud/read_all filters by product_name correctly.

        Creates versions for two different products and verifies that
        read_all only returns versions for the specified product.
        """
        # Create versions for product A
        client.post("/versions/?product_name=filterA&version=1.0.0")
        client.post("/versions/?product_name=filterA&version=1.1.0")

        # Create versions for product B
        client.post("/versions/?product_name=filterB&version=2.0.0")

        # Read all for product A
        response_a = client.get("/crud/read_all?product_name=filterA")
        assert response_a.status_code == 200
        data_a = response_a.json()
        assert len(data_a) == 2

        # Read all for product B
        response_b = client.get("/crud/read_all?product_name=filterB")
        assert response_b.status_code == 200
        data_b = response_b.json()
        assert len(data_b) == 1

    def test_read_all_missing_product_name(self, client: TestClient) -> None:
        """Test GET /crud/read_all returns 422 when product_name is missing.

        The product_name query parameter is required, so missing it should
        return a validation error.
        """
        response = client.get("/crud/read_all")
        assert response.status_code == 422  # Unprocessable Entity
