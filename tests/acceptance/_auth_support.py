"""Shared support for the P4 auth acceptance suite (not a collected test module).

The leading underscore keeps pytest from collecting this file (see
``python_files`` in ``pyproject.toml``). It provides the two things every auth
scenario needs and that the global acceptance ``conftest`` deliberately does not:

* an **env-configured, lifespan-active** :class:`~fastapi.testclient.TestClient`.
  Auth is default-OPEN until a provider is configured, and the app reads its
  :class:`~app.auth.auth_settings.AuthSettings` once at lifespan startup — so the
  ``LAVS_AUTH_*`` environment must be set *before* the client enters its ``with``
  block. :func:`auth_test_client` does exactly that.
* small end-to-end helpers (signup, verification-token capture, verify, login)
  so each scenario file stays behavior-focused (AAA).

The ``/auth`` endpoints are authored by the R1/R2 lanes and are not present in
this worktree yet; these helpers therefore drive the REAL routes and will go
green once those lanes merge. Nothing here stubs an endpoint.
"""

import re
import uuid
from collections.abc import Iterator
from contextlib import contextmanager

from fastapi.testclient import TestClient

# Deployment config that flips auth from default-OPEN to enforced. Password +
# API-key providers, sign-ups restricted to a single allow-listed domain.
AUTH_MODES = "password,apikey"
ALLOWED_DOMAIN = "example.com"
API_KEY = "acceptance-headless-key"
SESSION_COOKIE_NAME = "lavs_session"

# A password comfortably clearing any plausible strength floor R1 may impose.
DEFAULT_PASSWORD = "Acceptance-Pass-123!"

# ``secrets.token_urlsafe`` verification tokens are runs of URL-safe characters;
# the raw token is delivered once, in the email body captured by the mailer.
_TOKEN_QUERY_RE = re.compile(r"token=([A-Za-z0-9_-]+)")
_TOKEN_RUN_RE = re.compile(r"[A-Za-z0-9_-]{20,}")


@contextmanager
def auth_test_client(monkeypatch, *, api_key: str | None = None) -> Iterator[TestClient]:
    """Yield a lifespan-active client with the auth providers configured.

    The ``LAVS_AUTH_*`` environment is set before the client is constructed so
    the lifespan reads an enforced (fail-closed) configuration.

    Args:
        monkeypatch: The pytest ``monkeypatch`` fixture (auto-undone on teardown).
        api_key: When provided, the headless ``X-API-Key`` credential to
            configure; when ``None`` no API key is configured.

    Yields:
        A :class:`~fastapi.testclient.TestClient` whose lifespan has run.
    """
    monkeypatch.setenv("LAVS_AUTH_MODES", AUTH_MODES)
    monkeypatch.setenv("LAVS_ALLOWED_EMAIL_DOMAINS", ALLOWED_DOMAIN)
    if api_key is not None:
        monkeypatch.setenv("LAVS_API_KEY", api_key)
    else:
        monkeypatch.delenv("LAVS_API_KEY", raising=False)

    from app.main import app

    # Use an https base_url so the hardened ``Secure`` session cookie is carried
    # by the client's cookie jar — httpx (correctly) withholds a Secure cookie
    # over http, which is only a test-transport constraint, not app behaviour.
    with TestClient(app, base_url="https://testserver", raise_server_exceptions=False) as client:
        yield client


def unique_email(local: str = "engineer", domain: str = ALLOWED_DOMAIN) -> str:
    """Return a collision-free email in ``domain`` (defaults to the allow-list)."""
    return f"{local}-{uuid.uuid4().hex[:12]}@{domain}"


def verification_token_for(client: TestClient, email: str) -> str:
    """Recover the raw verification token from the captured email for ``email``.

    Args:
        client: The lifespan-active client (its ``app.state.mailer`` is the sink).
        email: The recipient whose most recent verification email to read.

    Returns:
        The raw verification token to POST to ``/auth/verify``.
    """
    mailer = client.app.state.mailer
    message = mailer.last_for(email)
    assert message is not None, f"no verification email was captured for {email!r}"

    query_match = _TOKEN_QUERY_RE.search(message.body)
    if query_match is not None:
        return query_match.group(1)

    candidates = _TOKEN_RUN_RE.findall(message.body)
    assert candidates, f"no token-shaped value found in email body: {message.body!r}"
    return max(candidates, key=len)


def signup(client: TestClient, email: str, password: str = DEFAULT_PASSWORD):
    """POST ``/auth/signup`` and return the raw response."""
    return client.post("/auth/signup", json={"email": email, "password": password})


def signup_and_verify(client: TestClient, email: str, password: str = DEFAULT_PASSWORD):
    """Run the full sign-up + email-verification flow, asserting each hop.

    Args:
        client: The lifespan-active client.
        email: The email to register (must be on the allow-listed domain).
        password: The password to register.

    Returns:
        The ``/auth/verify`` response (200 with the activated user body).
    """
    signup_response = signup(client, email, password)
    assert signup_response.status_code == 202, signup_response.text

    token = verification_token_for(client, email)
    verify_response = client.post("/auth/verify", json={"token": token})
    assert verify_response.status_code == 200, verify_response.text
    return verify_response


def login(client: TestClient, email: str, password: str = DEFAULT_PASSWORD):
    """POST ``/auth/login`` and return the raw response."""
    return client.post("/auth/login", json={"email": email, "password": password})


def assert_error_envelope(payload: object, expected_code: str) -> None:
    """Assert ``payload`` is the uniform ``{"error": {...}}`` envelope.

    Args:
        payload: The parsed JSON response body.
        expected_code: The stable machine-readable ``code`` that must be present.
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
