"""Acceptance: immutable version history + non-destructive rollback (P1 exit criterion).

P1 exit criterion + API_CONTRACT §3: versions are append-only and immutable.
``POST /versions/{id}/rollback`` marks the target ``rolled_back`` and re-activates
the prior version -- it never deletes a row, so the full history count is
preserved and the status transitions form an auditable ledger.

These tests drive the REAL HTTP endpoints through the FastAPI ``TestClient``.
Until the versions resource lane is merged the endpoints 404, so these
acceptance scenarios are expected to be RED.
"""

from fastapi.testclient import TestClient

_CREATED_OK = (200, 201)


def _seed_component(client: TestClient) -> str:
    """Create a product + component and return the component id.

    Args:
        client: The FastAPI test client.

    Returns:
        The created component's id.
    """
    product = client.post("/products", json={"name": "Aurora Platform"})
    assert product.status_code in _CREATED_OK, product.text
    product_id = product.json()["id"]

    component = client.post(
        "/components", json={"product_id": product_id, "name": "lavs-api", "kind": "service"}
    )
    assert component.status_code in _CREATED_OK, component.text
    return str(component.json()["id"])


def _create_version(client: TestClient, component_id: str, version: str) -> dict[str, object]:
    """Append an immutable version to a component.

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


def _history(client: TestClient, component_id: str) -> list[dict[str, object]]:
    """Read the full version history for a component.

    Args:
        client: The FastAPI test client.
        component_id: The component whose history to read.

    Returns:
        The list of version bodies.
    """
    response = client.get(f"/components/{component_id}/versions")
    assert response.status_code == 200, response.text
    return response.json()


class TestVersionHistoryAndRollback:
    """P1 exit criterion: rollback marks status and re-activates the prior, losing nothing."""

    def test_rollback_marks_target_rolled_back(self, client: TestClient) -> None:
        """Rolling back the active version transitions it to ``rolled_back``."""
        # Arrange
        component_id = _seed_component(client)
        _create_version(client, component_id, "1.0.0")
        latest = _create_version(client, component_id, "2.0.0")

        # Act
        response = client.post(f"/versions/{latest['id']}/rollback")

        # Assert
        assert response.status_code == 200, (
            f"rollback must return 200; got {response.status_code}: {response.text}"
        )
        rolled_back = next(v for v in _history(client, component_id) if v["id"] == latest["id"])
        assert rolled_back["status"] == "rolled_back"

    def test_rollback_reactivates_prior_version(self, client: TestClient) -> None:
        """After rollback exactly one *other* version is active (the re-activated prior)."""
        # Arrange
        component_id = _seed_component(client)
        first = _create_version(client, component_id, "1.0.0")
        latest = _create_version(client, component_id, "2.0.0")

        # Act
        client.post(f"/versions/{latest['id']}/rollback")

        # Assert
        history = _history(client, component_id)
        active = [v for v in history if v["status"] == "active"]
        assert len(active) == 1, f"exactly one version must be active after rollback; got {active}"
        assert active[0]["id"] != latest["id"], "the rolled-back version must not remain active"
        assert active[0]["id"] == first["id"], "the prior version must be re-activated"

    def test_rollback_preserves_full_history_count(self, client: TestClient) -> None:
        """No version is deleted: the history count is identical before and after rollback."""
        # Arrange
        component_id = _seed_component(client)
        _create_version(client, component_id, "1.0.0")
        _create_version(client, component_id, "2.0.0")
        latest = _create_version(client, component_id, "3.0.0")
        count_before = len(_history(client, component_id))

        # Act
        client.post(f"/versions/{latest['id']}/rollback")

        # Assert
        count_after = len(_history(client, component_id))
        assert count_before == 3
        assert count_after == count_before, "rollback must be non-destructive (no version lost)"

    def test_rolled_back_version_still_present_in_history(self, client: TestClient) -> None:
        """The rolled-back version remains retrievable -- immutability, not deletion."""
        # Arrange
        component_id = _seed_component(client)
        _create_version(client, component_id, "1.0.0")
        latest = _create_version(client, component_id, "2.0.0")

        # Act
        client.post(f"/versions/{latest['id']}/rollback")

        # Assert
        history_ids = {v["id"] for v in _history(client, component_id)}
        assert latest["id"] in history_ids, "the rolled-back version must remain in history"
