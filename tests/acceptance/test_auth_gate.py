"""Acceptance: API-key auth gate (P0 'Wire auth (seed)').

ROADMAP P0 acceptance: "auth enforced when ``LAVS_API_KEY`` is set". The API-key
dependency in ``app/security/api_key.py`` must be applied to the data routers.

Behavior under test (from ``app/security/api_key.py`` and API_CONTRACT.md §1):
  * ``LAVS_API_KEY`` unset  -> routes are open (optional auth).
  * ``LAVS_API_KEY`` set     -> a request WITHOUT ``X-API-Key`` is rejected with 401.
  * ``LAVS_API_KEY`` set     -> a request WITH the correct key is admitted.

These tests use ``monkeypatch`` to control the environment. The api_key dependency
reads the environment at request time, so the same app instance honors changes made
before each request. NOTE: until the P0 auth-wiring lane lands, the "set" cases are
expected to be RED (routes are currently unprotected).
"""

import pytest
from fastapi.testclient import TestClient

# A representative protected DATA route (GET, no body required). When auth wiring
# lands this route must require a valid principal per API_CONTRACT.md §3.
_PROTECTED_DATA_ROUTE = "/versions/?product_name=acceptance_auth_probe"
_API_KEY_ENV_VAR = "LAVS_API_KEY"
_API_KEY_HEADER = "X-API-Key"
_VALID_KEY = "acceptance-secret-key"


class TestApiKeyGate:
    """P0 exit criterion: API-key auth is enforced when configured."""

    def test_route_open_when_api_key_unset(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """With ``LAVS_API_KEY`` unset, the data route is open (no 401)."""
        monkeypatch.delenv(_API_KEY_ENV_VAR, raising=False)

        response = client.get(_PROTECTED_DATA_ROUTE)

        # Optional auth: request must not be rejected for missing credentials.
        assert response.status_code != 401, (
            "Route must be open when LAVS_API_KEY is unset; "
            f"got {response.status_code}: {response.text}"
        )

    def test_missing_key_rejected_when_api_key_set(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """With ``LAVS_API_KEY`` set, a request lacking ``X-API-Key`` returns 401.

        RED until P0 auth wiring lands.
        """
        monkeypatch.setenv(_API_KEY_ENV_VAR, _VALID_KEY)

        response = client.get(_PROTECTED_DATA_ROUTE)

        assert response.status_code == 401, (
            "Protected data route must return 401 without X-API-Key when "
            f"LAVS_API_KEY is set; got {response.status_code}: {response.text}"
        )

    def test_correct_key_admitted_when_api_key_set(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """With ``LAVS_API_KEY`` set, the correct ``X-API-Key`` is admitted.

        The route must not reject the request for auth reasons (no 401/403). A
        successful auth passes through to the handler.
        """
        monkeypatch.setenv(_API_KEY_ENV_VAR, _VALID_KEY)

        response = client.get(
            _PROTECTED_DATA_ROUTE,
            headers={_API_KEY_HEADER: _VALID_KEY},
        )

        assert response.status_code not in (401, 403), (
            "Correct X-API-Key must be admitted when LAVS_API_KEY is set; "
            f"got {response.status_code}: {response.text}"
        )

    def test_wrong_key_rejected_when_api_key_set(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """With ``LAVS_API_KEY`` set, an incorrect key is rejected (401 or 403).

        RED until P0 auth wiring lands.
        """
        monkeypatch.setenv(_API_KEY_ENV_VAR, _VALID_KEY)

        response = client.get(
            _PROTECTED_DATA_ROUTE,
            headers={_API_KEY_HEADER: "the-wrong-key"},
        )

        assert response.status_code in (401, 403), (
            "Wrong X-API-Key must be rejected when LAVS_API_KEY is set; "
            f"got {response.status_code}: {response.text}"
        )
