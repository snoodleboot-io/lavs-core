"""Acceptance: non-destructive rollback (P0 'Non-destructive rollback').

ROADMAP P0: ``rollback_to_previous_patch_version.py`` currently ``DELETE``s the
current row. It must instead flag status (``rolled_back``) so history is preserved,
and re-activate the prior version.

API_CONTRACT.md §4: rollback "sets the current ``active`` version to ``rolled_back``
and re-activates the prior version. History is never deleted."

This test creates a base version, a patch (so there are >= 2 rows), records the row
count, performs a rollback, then asserts:
  1. NO row was deleted (history preserved) -- row count does not decrease.
  2. The prior version becomes the active/latest version.

Until the P0 non-destructive-rollback lane lands, assertion (1) is expected to be RED
(the current implementation deletes the current row).
"""

from fastapi.testclient import TestClient

_PRODUCT = "rollback_acceptance_probe"


def _history_row_count(client: TestClient) -> int:
    """Return the number of persisted version rows for the probe product.

    Args:
        client: The acceptance ``TestClient``.

    Returns:
        Count of rows returned by the version-history endpoint.
    """
    response = client.get(f"/versions/?product_name={_PRODUCT}")
    assert response.status_code == 200, (
        f"history fetch failed: {response.status_code}: {response.text}"
    )
    payload = response.json()
    assert isinstance(payload, list), f"expected list history, got: {payload!r}"
    return len(payload)


class TestRollbackPreservesHistory:
    """P0 exit criterion: rollback preserves history and re-activates the prior version."""

    def test_rollback_does_not_delete_and_reactivates_prior(self, client: TestClient) -> None:
        """After a rollback, no row is removed and the prior version is active."""
        # Base version 1.0.0
        base = client.post(f"/versions/?product_name={_PRODUCT}&version=1.0.0")
        assert base.status_code < 400, f"base create failed: {base.text}"

        # A patch -> 1.0.1 (a second, current/active version).
        patch = client.post(f"/patch/?product_name={_PRODUCT}")
        assert patch.status_code < 400, f"patch create failed: {patch.text}"

        rows_before = _history_row_count(client)
        assert rows_before >= 2, f"expected >= 2 versions before rollback, got {rows_before}"

        # Roll back the current (active) version.
        rollback = client.post(f"/patch/rollback?product_name={_PRODUCT}")
        assert rollback.status_code < 400, f"rollback failed: {rollback.text}"

        # (1) History must be preserved -- no row deleted.
        rows_after = _history_row_count(client)
        assert rows_after >= rows_before, (
            f"Rollback must NOT delete history rows; had {rows_before} before, {rows_after} after"
        )

        # (2) The prior version (1.0.0) must now be the active/latest version.
        latest = client.get(f"/versions/latest?product_name={_PRODUCT}")
        assert latest.status_code == 200, f"latest fetch failed: {latest.text}"
        latest_data = latest.json()
        assert (latest_data["major"], latest_data["minor"], latest_data["patch"]) == (
            1,
            0,
            0,
        ), f"prior version 1.0.0 must be active after rollback; got {latest_data!r}"
