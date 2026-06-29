"""Acceptance: anchored semver validation (P0 'Anchor the semver regex').

ROADMAP P0: the version validator in
``app/models/requests/application_and_version_model.py`` uses an UNANCHORED regex
``[0-9]+\\.[0-9]+\\.[0-9]+`` so ``1.2.3.4`` and ``1.2.3abc`` incorrectly pass. It must
be anchored (``^...$``).

API_CONTRACT.md §4: ``version`` must match ``^\\d+\\.\\d+\\.\\d+$`` (optionally a
``-prerelease`` suffix); the server rejects others with ``422 validation_error``.

Until the P0 regex-anchoring lane lands, the malformed cases are expected to be RED
(the current validator admits them, producing a 2xx instead of 422).
"""

import pytest
from fastapi.testclient import TestClient

_PRODUCT = "semver_acceptance_probe"


class TestSemverValidation:
    """P0 exit criterion: only strict ``X.Y.Z`` semver is accepted."""

    @pytest.mark.parametrize(
        "bad_version",
        [
            "1.2.3.4",
            "1.2.3abc",
        ],
    )
    def test_malformed_semver_rejected_with_422(self, client: TestClient, bad_version: str) -> None:
        """Creating a version with a malformed string yields 422."""
        response = client.post(f"/versions/?product_name={_PRODUCT}&version={bad_version}")

        assert response.status_code == 422, (
            f"Malformed version {bad_version!r} must be rejected with 422; "
            f"got {response.status_code}: {response.text}"
        )

    def test_valid_semver_accepted(self, client: TestClient) -> None:
        """A valid ``1.2.3`` version is accepted (not a validation error)."""
        response = client.post(f"/versions/?product_name={_PRODUCT}&version=1.2.3")

        assert response.status_code != 422, (
            "Valid semver '1.2.3' must NOT be rejected as a validation error; "
            f"got {response.status_code}: {response.text}"
        )
        assert response.status_code < 400, (
            f"Valid semver '1.2.3' must be accepted; got {response.status_code}: {response.text}"
        )
