"""Acceptance: EE Stytch callback, session round-trip, and /meta (API_CONTRACT §1–2).

Drives the REAL ``POST /auth/stytch/callback`` against an EE-configured app
whose Stytch verification seam is a fake installed on
``app.state.stytch_verifier`` — no network is ever touched. The happy path
proves a verifying token mints the same hardened ``lavs_session`` cookie as
``/auth/login`` and that the cookie then authenticates ``GET /auth/me`` and a
protected resource route (stytch-only deployments still resolve the session
cookie). Negatives pin the fail-closed posture: an expired/garbage token, a
disabled account, and a callback on a non-EE deployment all answer the same
generic 401 envelope (no enumeration, no "disabled route" fingerprint). The
``/meta`` matrix asserts EE+stytch advertises the mode and the publishable
public token while the OSS response stays byte-compatible.
"""

from collections.abc import Iterator
from contextlib import contextmanager

import duckdb
import pytest
from fastapi.testclient import TestClient

from app.auth.stytch.stytch_verification import StytchVerification
from app.auth.stytch.stytch_verifier import StytchVerifier
from app.auth.users.user_repository import UserRepository
from tests.acceptance._auth_support import (
    SESSION_COOKIE_NAME,
    assert_error_envelope,
    auth_test_client,
    unique_email,
)

VALID_TOKEN = "WJtR5BCy38Szd5AfoDpf0iqFKEt4EE5JhjlWUY7l3FtY"
STYTCH_USER_ID = "user-test-16d9ba61-97a1-4ba4-9720-b03761dc50c6"
PUBLIC_TOKEN = "public-token-test-acceptance"


class FakeStytchVerifier(StytchVerifier):
    """A verifier accepting a fixed token map — the injected SDK stand-in."""

    def __init__(self, known: dict[str, StytchVerification]) -> None:
        """Initialise the fake.

        Args:
            known: Map of accepted raw tokens to the identity they verify as.
        """
        self._known = known

    async def verify(self, token: str) -> StytchVerification | None:
        """Resolve a token against the fixed map (None when unknown)."""
        return self._known.get(token)


@contextmanager
def stytch_test_client(
    monkeypatch,
    *,
    edition: str | None = "ee",
    modes: str = "stytch",
    public_token: str | None = PUBLIC_TOKEN,
    allowed_domains: str | None = None,
) -> Iterator[TestClient]:
    """Yield a lifespan-active client configured for the Stytch (EE) mode.

    The ``LAVS_*`` environment is set before the client is constructed so the
    lifespan reads the intended edition and modes. No real Stytch credentials
    are configured — tests install a :class:`FakeStytchVerifier` on
    ``app.state.stytch_verifier`` before exercising the callback.

    Args:
        monkeypatch: The pytest ``monkeypatch`` fixture (auto-undone on teardown).
        edition: The ``LAVS_EDITION`` value (``None`` leaves it unset — OSS).
        modes: The ``LAVS_AUTH_MODES`` comma list.
        public_token: The publishable token to expose, or ``None`` for unset.
        allowed_domains: The ``LAVS_ALLOWED_EMAIL_DOMAINS`` comma list, or
            ``None`` for unset (allow all).

    Yields:
        A :class:`~fastapi.testclient.TestClient` whose lifespan has run.
    """
    monkeypatch.setenv("LAVS_AUTH_MODES", modes)
    if allowed_domains is not None:
        monkeypatch.setenv("LAVS_ALLOWED_EMAIL_DOMAINS", allowed_domains)
    else:
        monkeypatch.delenv("LAVS_ALLOWED_EMAIL_DOMAINS", raising=False)
    if edition is not None:
        monkeypatch.setenv("LAVS_EDITION", edition)
    else:
        monkeypatch.delenv("LAVS_EDITION", raising=False)
    if public_token is not None:
        monkeypatch.setenv("LAVS_STYTCH_PUBLIC_TOKEN", public_token)
    else:
        monkeypatch.delenv("LAVS_STYTCH_PUBLIC_TOKEN", raising=False)
    monkeypatch.delenv("LAVS_API_KEY", raising=False)
    monkeypatch.delenv("LAVS_STYTCH_PROJECT_ID", raising=False)
    monkeypatch.delenv("LAVS_STYTCH_SECRET", raising=False)

    from app.main import app

    # https base_url so the Secure lavs_session cookie rides the client's
    # cookie jar (a test-transport constraint, not app behaviour).
    with TestClient(app, base_url="https://testserver", raise_server_exceptions=False) as client:
        yield client


def _install_fake_verifier(client: TestClient, email: str) -> None:
    """Install a fake verifier accepting ``VALID_TOKEN`` for ``email``."""
    client.app.state.stytch_verifier = FakeStytchVerifier(
        {VALID_TOKEN: StytchVerification(user_id=STYTCH_USER_ID, email=email)}
    )


def _callback(client: TestClient, token: str):
    """POST ``/auth/stytch/callback`` and return the raw response."""
    return client.post("/auth/stytch/callback", json={"stytch_token": token})


@pytest.fixture
def stytch_client(monkeypatch, test_db: str):
    """A lifespan-active EE client with stytch-only auth configured."""
    with stytch_test_client(monkeypatch) as client:
        yield client


def _session_set_cookie(response) -> str:
    """Return the ``Set-Cookie`` header line that sets the session cookie."""
    cookie_headers = response.headers.get_list("set-cookie")
    for header in cookie_headers:
        if header.startswith(f"{SESSION_COOKIE_NAME}="):
            return header
    raise AssertionError(
        f"no {SESSION_COOKIE_NAME} Set-Cookie header on callback response; got {cookie_headers}"
    )


class TestStytchCallback:
    """The callback exchanges a verified token for the normal LAVS session."""

    def test_valid_token_sets_the_hardened_session_cookie(self, stytch_client: TestClient) -> None:
        """A verifying token returns 200, the user body, and the hardened cookie."""
        # Arrange
        email = unique_email()
        _install_fake_verifier(stytch_client, email)

        # Act
        response = _callback(stytch_client, VALID_TOKEN)

        # Assert — same cookie contract as /auth/login
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["email"] == email
        assert body["status"] == "active"
        set_cookie = _session_set_cookie(response)
        assert "httponly" in set_cookie.lower(), set_cookie
        assert "samesite=lax" in set_cookie.lower(), set_cookie
        assert "secure" in set_cookie.lower(), set_cookie
        assert "path=/" in set_cookie.lower(), set_cookie

    def test_callback_session_authenticates_auth_me(self, stytch_client: TestClient) -> None:
        """The minted session cookie round-trips through ``GET /auth/me``."""
        # Arrange
        email = unique_email()
        _install_fake_verifier(stytch_client, email)
        callback_response = _callback(stytch_client, VALID_TOKEN)
        assert callback_response.status_code == 200, callback_response.text

        # Act — the client's cookie jar replays the session cookie automatically
        response = stytch_client.get("/auth/me")

        # Assert
        assert response.status_code == 200, response.text
        assert response.json()["email"] == email

    def test_callback_session_authenticates_resource_routes(
        self, stytch_client: TestClient
    ) -> None:
        """Stytch-only deployments still resolve the session cookie on resources."""
        # Arrange — before any credential the deployment fails closed
        unauthenticated = stytch_client.get("/products")
        assert unauthenticated.status_code == 401, unauthenticated.text
        email = unique_email()
        _install_fake_verifier(stytch_client, email)
        assert _callback(stytch_client, VALID_TOKEN).status_code == 200

        # Act
        response = stytch_client.get("/products")

        # Assert
        assert response.status_code == 200, response.text

    def test_repeat_callback_reuses_the_same_user(self, stytch_client: TestClient) -> None:
        """A second callback for the same email maps to the same user row."""
        # Arrange
        email = unique_email()
        _install_fake_verifier(stytch_client, email)
        first = _callback(stytch_client, VALID_TOKEN)
        assert first.status_code == 200, first.text

        # Act
        second = _callback(stytch_client, VALID_TOKEN)

        # Assert — idempotent upsert: one account, stable id
        assert second.status_code == 200, second.text
        assert second.json()["id"] == first.json()["id"]

    def test_pending_user_is_activated_by_stytch_verification(
        self, monkeypatch, test_db: str
    ) -> None:
        """A pending password sign-up becomes active after Stytch verifies the email."""
        # Arrange — password + stytch both enabled; user signs up but never verifies
        with stytch_test_client(monkeypatch, modes="password,stytch") as client:
            email = unique_email()
            signup_response = client.post(
                "/auth/signup", json={"email": email, "password": "Acceptance-Pass-123!"}
            )
            assert signup_response.status_code == 202, signup_response.text
            _install_fake_verifier(client, email)

            # Act — Stytch has verified the same email
            response = _callback(client, VALID_TOKEN)

            # Assert — the account is activated, not duplicated
            assert response.status_code == 200, response.text
            assert response.json()["status"] == "active"
            me_response = client.get("/auth/me")
            assert me_response.status_code == 200, me_response.text
            assert me_response.json()["status"] == "active"

    def test_garbage_token_returns_generic_401(self, stytch_client: TestClient) -> None:
        """A token the verifier rejects answers the single generic 401."""
        # Arrange
        _install_fake_verifier(stytch_client, unique_email())

        # Act
        response = _callback(stytch_client, "utterly-garbage-token")

        # Assert
        assert response.status_code == 401, response.text
        assert_error_envelope(response.json(), "unauthorized")

    def test_expired_token_is_indistinguishable_from_garbage(
        self, stytch_client: TestClient
    ) -> None:
        """An expired (formerly valid) token gets the identical 401 shape."""
        # Arrange — a verifier that no longer accepts any token (all expired)
        stytch_client.app.state.stytch_verifier = FakeStytchVerifier({})

        # Act
        response = _callback(stytch_client, VALID_TOKEN)

        # Assert
        assert response.status_code == 401, response.text
        assert_error_envelope(response.json(), "unauthorized")

    def test_disabled_account_returns_generic_401(self, stytch_client: TestClient) -> None:
        """A disabled user cannot re-enter through Stytch — same generic 401."""
        # Arrange — create the account via a first callback, then disable it
        email = unique_email()
        _install_fake_verifier(stytch_client, email)
        first = _callback(stytch_client, VALID_TOKEN)
        assert first.status_code == 200, first.text
        connection = stytch_client.app.state.db_connection
        connection.execute("UPDATE users SET status = ? WHERE email = ?", ["disabled", email])

        # Act
        response = _callback(stytch_client, VALID_TOKEN)

        # Assert
        assert response.status_code == 401, response.text
        assert_error_envelope(response.json(), "unauthorized")

    def test_unverified_only_email_returns_generic_401(self, stytch_client: TestClient) -> None:
        """An identity with no **verified** email is refused — no takeover lane."""
        # Arrange — the verifier resolved an identity but surfaced no verified
        # email (StytchVerification.email is None in that case)
        stytch_client.app.state.stytch_verifier = FakeStytchVerifier(
            {VALID_TOKEN: StytchVerification(user_id=STYTCH_USER_ID, email=None)}
        )

        # Act
        response = _callback(stytch_client, VALID_TOKEN)

        # Assert
        assert response.status_code == 401, response.text
        assert_error_envelope(response.json(), "unauthorized")

    def test_concurrent_first_sight_race_adopts_the_winning_row(
        self, stytch_client: TestClient, monkeypatch
    ) -> None:
        """A lost insert race on the unique email maps to the winner's row.

        Simulates two first-sight callbacks racing: our read saw no row, the
        concurrent request inserted one, and our insert hits the unique-email
        constraint. The callback must adopt the existing row instead of
        surfacing a duplicate-key 500.
        """
        # Arrange — create_user performs the real insert (the concurrent
        # winner) and then raises the constraint violation our own insert hits
        email = unique_email()
        _install_fake_verifier(stytch_client, email)
        original_create = UserRepository.create_user

        # design-decision-override: the closure must capture original_create to
        # both perform the winner's insert and raise the loser's violation.
        async def racing_create(self, conn, **kwargs):
            await original_create(self, conn, **kwargs)
            raise duckdb.ConstraintException(
                "Duplicate key violates unique constraint on users.email"
            )

        monkeypatch.setattr(UserRepository, "create_user", racing_create)

        # Act
        response = _callback(stytch_client, VALID_TOKEN)

        # Assert — 200 with the row the "winner" created
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["email"] == email
        assert body["status"] == "active"
        row = stytch_client.app.state.db_connection.execute(
            "SELECT id FROM users WHERE email = ?", [email]
        ).fetchone()
        assert row is not None
        assert body["id"] == str(row[0])

    def test_missing_token_field_is_a_422(self, stytch_client: TestClient) -> None:
        """An omitted ``stytch_token`` is malformed input, not bad credentials."""
        # Act
        response = stytch_client.post("/auth/stytch/callback", json={})

        # Assert
        assert response.status_code == 422, response.text


class TestStytchDomainAllowList:
    """The email-domain allow-list holds on the Stytch lane (generic 401)."""

    def test_first_sight_outside_allowlist_returns_generic_401(
        self, monkeypatch, test_db: str
    ) -> None:
        """A first-sight verified email outside the allow-list is refused."""
        # Arrange — allow-list pins example.com; Stytch verifies an outsider
        with stytch_test_client(monkeypatch, allowed_domains="example.com") as client:
            outsider = unique_email(domain="not-allowed.test")
            _install_fake_verifier(client, outsider)

            # Act
            response = _callback(client, VALID_TOKEN)

            # Assert — generic 401 (not signup's 403: no allow-list fingerprint)
            assert response.status_code == 401, response.text
            assert_error_envelope(response.json(), "unauthorized")
            row = client.app.state.db_connection.execute(
                "SELECT id FROM users WHERE email = ?", [outsider]
            ).fetchone()
            assert row is None, "no user row may be created for a disallowed domain"

    def test_existing_user_outside_tightened_allowlist_returns_generic_401(
        self, monkeypatch, test_db: str
    ) -> None:
        """Defense in depth: a tightened allow-list also locks out mapped users."""
        # Arrange — the user maps in while their domain is allowed…
        email = unique_email()
        with stytch_test_client(monkeypatch) as client:
            _install_fake_verifier(client, email)
            assert _callback(client, VALID_TOKEN).status_code == 200

        # …then the operator tightens the allow-list to another domain
        with stytch_test_client(monkeypatch, allowed_domains="other-corp.test") as client:
            _install_fake_verifier(client, email)

            # Act
            response = _callback(client, VALID_TOKEN)

            # Assert — the existing mapping does not grandfather them in
            assert response.status_code == 401, response.text
            assert_error_envelope(response.json(), "unauthorized")

    def test_allowlisted_domain_still_authenticates(self, monkeypatch, test_db: str) -> None:
        """A verified email inside the allow-list proceeds normally."""
        # Arrange
        with stytch_test_client(monkeypatch, allowed_domains="example.com") as client:
            email = unique_email()
            _install_fake_verifier(client, email)

            # Act
            response = _callback(client, VALID_TOKEN)

            # Assert
            assert response.status_code == 200, response.text
            assert response.json()["email"] == email


class TestStytchDisabledOnOss:
    """Without EE the stytch mode — and its callback — stay dark."""

    def test_callback_on_oss_returns_generic_401(self, monkeypatch, test_db: str) -> None:
        """On OSS the callback answers the same generic 401 as a bad credential."""
        # Arrange — stytch listed in modes but no EE edition: token is ignored
        with stytch_test_client(monkeypatch, edition=None) as client:
            _install_fake_verifier(client, unique_email())

            # Act — even a token the verifier would accept is refused
            response = _callback(client, VALID_TOKEN)

            # Assert
            assert response.status_code == 401, response.text
            assert_error_envelope(response.json(), "unauthorized")

    def test_meta_on_oss_does_not_advertise_stytch(self, monkeypatch, test_db: str) -> None:
        """OSS ``/meta`` never lists stytch nor leaks the public token."""
        # Arrange
        with stytch_test_client(monkeypatch, edition=None) as client:
            # Act
            response = client.get("/meta")

            # Assert
            assert response.status_code == 200, response.text
            body = response.json()
            assert body["edition"] == "oss"
            assert "stytch" not in body["auth_modes"]
            assert "stytch_public_token" not in body


class TestMetaOnEe:
    """EE ``/meta`` advertises the stytch mode and the publishable token."""

    def test_meta_reports_ee_stytch_and_public_token(self, stytch_client: TestClient) -> None:
        """``GET /meta`` returns edition ee, the stytch mode, and the token."""
        # Act
        response = stytch_client.get("/meta")

        # Assert
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["edition"] == "ee"
        assert "stytch" in body["auth_modes"]
        assert body["stytch_public_token"] == PUBLIC_TOKEN

    def test_meta_without_public_token_omits_the_key(self, monkeypatch, test_db: str) -> None:
        """An EE deployment with no publishable token configured omits the key."""
        # Arrange
        with stytch_test_client(monkeypatch, public_token=None) as client:
            # Act
            response = client.get("/meta")

            # Assert
            assert response.status_code == 200, response.text
            body = response.json()
            assert body["edition"] == "ee"
            assert "stytch_public_token" not in body


class TestOssMetaUnchanged:
    """The pre-EE OSS ``/meta`` behaviour is untouched (backward-compatible)."""

    def test_password_apikey_meta_shape_is_stable(self, monkeypatch, test_db: str) -> None:
        """The OSS password/apikey deployment reports the same modes as before."""
        # Arrange
        with auth_test_client(monkeypatch) as client:
            # Act
            response = client.get("/meta")

            # Assert
            assert response.status_code == 200, response.text
            body = response.json()
            assert body["edition"] == "oss"
            assert set(body["auth_modes"]) == {"password", "apikey"}
            # Byte-compatible with the pre-EE body: the key is absent, not null
            assert "stytch_public_token" not in body
