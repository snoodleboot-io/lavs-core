"""Acceptance: the P4 auth foundation is wired end to end.

Drives the real application (via the lifespan-active ``client`` fixture) to prove
the foundation boots: health is up, the auth spine and mailer are on
``app.state``, the auth tables exist, ``/meta`` advertises the deployment, a
resource route stays open when nothing is configured, and — with a configured
resolver — the same route fails closed with a 401 envelope.
"""

from fastapi.testclient import TestClient

from app.auth.auth_mode import AuthMode
from app.auth.auth_resolver import AuthResolver
from app.auth.auth_resolver_factory import AuthResolverFactory
from app.auth.auth_settings import AuthSettings

_AUTH_TABLES = {"users", "sessions", "email_verification_tokens"}


class TestFoundationBoot:
    """Startup wiring and public surface."""

    def test_health_is_ok(self, client: TestClient) -> None:
        """The liveness probe answers 200."""
        # Act
        response = client.get("/health")

        # Assert
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_app_state_has_resolver_and_mailer(self, client: TestClient) -> None:
        """The lifespan populated the auth resolver and the capture mailer."""
        # Act
        state = client.app.state

        # Assert
        assert isinstance(state.auth_resolver, AuthResolver)
        assert state.mailer is not None
        assert state.auth_registry is not None

    def test_auth_tables_exist(self, client: TestClient) -> None:
        """The users/sessions/verification tables were created at startup."""
        # Arrange
        connection = client.app.state.db_connection

        # Act
        rows = connection.execute("SHOW ALL TABLES").fetchall()
        table_names = {row[2] for row in rows}

        # Assert
        assert _AUTH_TABLES.issubset(table_names)

    def test_meta_reports_edition_and_modes(self, client: TestClient) -> None:
        """``GET /meta`` is public and reports edition + auth modes."""
        # Act
        response = client.get("/meta")

        # Assert
        assert response.status_code == 200
        body = response.json()
        assert body["edition"] == "oss"
        assert isinstance(body["auth_modes"], list)


class TestFoundationAuthGate:
    """Open-when-unconfigured vs fail-closed-when-configured."""

    def test_resource_route_open_when_unconfigured(self, client: TestClient) -> None:
        """With no auth configured, a resource route is reachable with no creds."""
        # Act
        response = client.get("/products")

        # Assert
        assert response.status_code == 200

    def test_resource_route_fail_closed_when_configured(self, client: TestClient) -> None:
        """A password-configured resolver rejects a credential-less request 401."""
        # Arrange — swap in a configured resolver (env plumbing in-test is awkward)
        app = client.app
        original = app.state.auth_resolver
        settings = AuthSettings(modes={AuthMode.PASSWORD})
        app.state.auth_resolver = AuthResolverFactory.build_resolver(settings)

        try:
            # Act
            response = client.get("/products")

            # Assert
            assert response.status_code == 401
            assert response.json()["error"]["code"] == "unauthorized"
        finally:
            app.state.auth_resolver = original
