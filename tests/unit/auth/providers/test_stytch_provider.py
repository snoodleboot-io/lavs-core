"""Unit tests for :class:`StytchProvider`."""

from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase

from fastapi import Request

from app.auth.principal_kind import PrincipalKind
from app.auth.providers.stytch_provider import StytchProvider
from app.auth.stytch.stytch_verification import StytchVerification
from app.auth.stytch.stytch_verifier import StytchVerifier
from app.auth.users.user_repository import UserRepository
from app.connections.db_session import DbSession


class FakeStytchVerifier(StytchVerifier):
    """A verifier resolving a fixed token map — no SDK, no network."""

    def __init__(self, known: dict[str, StytchVerification]) -> None:
        """Initialise the fake.

        Args:
            known: Map of accepted raw tokens to the identity they verify as.
        """
        self._known = known

    async def verify(self, token: str) -> StytchVerification | None:
        """Resolve a token against the fixed map (None when unknown)."""
        return self._known.get(token)


class FakeUserRepository(UserRepository):
    """A users store answering ``get_user_by_email`` from a fixed row map."""

    def __init__(self, rows_by_email: dict[str, tuple[object, ...]]) -> None:
        """Initialise the fake.

        Args:
            rows_by_email: Map of email to the raw users row it resolves to.
        """
        self._rows_by_email = rows_by_email

    async def get_user_by_email(self, conn: DbSession, email: str) -> tuple[object, ...] | None:
        """Resolve an email against the fixed map (None when unmapped)."""
        return self._rows_by_email.get(email)


def _user_row(user_id: str, email: str, status: str) -> tuple[object, ...]:
    """Build a raw users row ``(id, email, password_hash, status, edition, created_at)``."""
    return (user_id, email, "argon2-hash-unused", status, "ee", None)


def _request(cookies: dict[str, str], db_connection: object = "live-db-session") -> Request:
    """Build a request carrying the given cookies and app-state db connection.

    Args:
        cookies: Cookie name/value pairs to present.
        db_connection: The value exposed as ``app.state.db_connection``
            (``None`` models a deployment without a live database).

    Returns:
        A request carrying the cookies and state.
    """
    headers: list[tuple[bytes, bytes]] = []
    if cookies:
        cookie_line = "; ".join(f"{name}={value}" for name, value in cookies.items())
        headers.append((b"cookie", cookie_line.encode()))
    app = SimpleNamespace(state=SimpleNamespace(db_connection=db_connection))
    scope = {"type": "http", "method": "GET", "path": "/", "headers": headers, "app": app}
    return Request(scope)


class TestStytchProvider(IsolatedAsyncioTestCase):
    """Stytch-cookie authentication resolves the mapped, active LAVS user."""

    def setUp(self) -> None:
        """Build a provider whose verified email maps to an active LAVS user."""
        self._verification = StytchVerification(
            user_id="user-test-00000000-0000-0000-0000-000000000001",
            email="Engineer@Example.com",
        )
        self._lavs_user_id = "01LAVSUSERID0000000000000A"
        self._provider = StytchProvider(
            edition="ee",
            verifier=FakeStytchVerifier({"good-token": self._verification}),
            user_repository=FakeUserRepository(
                {
                    "engineer@example.com": _user_row(
                        self._lavs_user_id, "engineer@example.com", "active"
                    )
                }
            ),
        )

    async def test_valid_session_jwt_cookie_returns_lavs_user_principal(self) -> None:
        """A verifying cookie mints a principal carrying the **LAVS** identity.

        The verified email is normalized (trim/lower) before the lookup, and
        the principal carries the LAVS user id and row email — never the raw
        Stytch id, so ``/auth/me`` reflects the real account row.
        """
        # Arrange
        request = _request({"stytch_session_jwt": "good-token"})

        # Act
        principal = await self._provider.authenticate(request)

        # Assert
        assert principal is not None
        assert principal.kind is PrincipalKind.USER
        assert principal.id == self._lavs_user_id
        assert principal.email == "engineer@example.com"
        assert principal.edition == "ee"

    async def test_session_token_cookie_is_the_fallback(self) -> None:
        """Without a JWT cookie the ``stytch_session`` cookie is verified."""
        # Arrange
        request = _request({"stytch_session": "good-token"})

        # Act
        principal = await self._provider.authenticate(request)

        # Assert
        assert principal is not None
        assert principal.id == self._lavs_user_id

    async def test_no_stytch_cookie_returns_none(self) -> None:
        """A request with no Stytch cookie is not-me — None, never a raise."""
        # Arrange
        request = _request({"lavs_session": "some-other-cookie"})

        # Act / Assert
        assert await self._provider.authenticate(request) is None

    async def test_empty_cookie_value_returns_none(self) -> None:
        """An empty Stytch cookie value authenticates nobody."""
        # Arrange
        request = _request({"stytch_session_jwt": ""})

        # Act / Assert
        assert await self._provider.authenticate(request) is None

    async def test_invalid_token_returns_none(self) -> None:
        """A token the verifier rejects resolves to None (not an exception)."""
        # Arrange
        request = _request({"stytch_session_jwt": "expired-or-garbage"})

        # Act / Assert
        assert await self._provider.authenticate(request) is None

    async def test_unmapped_stytch_user_returns_none(self) -> None:
        """A verified identity with no LAVS user row authenticates nobody."""
        # Arrange
        provider = StytchProvider(
            edition="ee",
            verifier=FakeStytchVerifier({"good-token": self._verification}),
            user_repository=FakeUserRepository({}),
        )
        request = _request({"stytch_session_jwt": "good-token"})

        # Act / Assert
        assert await provider.authenticate(request) is None

    async def test_disabled_lavs_user_returns_none(self) -> None:
        """A disabled LAVS account cannot bypass its disablement via Stytch."""
        # Arrange
        provider = StytchProvider(
            edition="ee",
            verifier=FakeStytchVerifier({"good-token": self._verification}),
            user_repository=FakeUserRepository(
                {
                    "engineer@example.com": _user_row(
                        self._lavs_user_id, "engineer@example.com", "disabled"
                    )
                }
            ),
        )
        request = _request({"stytch_session_jwt": "good-token"})

        # Act / Assert
        assert await provider.authenticate(request) is None

    async def test_pending_lavs_user_returns_none(self) -> None:
        """A not-yet-active (pending) LAVS account authenticates nobody."""
        # Arrange
        provider = StytchProvider(
            edition="ee",
            verifier=FakeStytchVerifier({"good-token": self._verification}),
            user_repository=FakeUserRepository(
                {
                    "engineer@example.com": _user_row(
                        self._lavs_user_id, "engineer@example.com", "pending"
                    )
                }
            ),
        )
        request = _request({"stytch_session_jwt": "good-token"})

        # Act / Assert
        assert await provider.authenticate(request) is None

    async def test_verification_without_email_returns_none(self) -> None:
        """An identity with no verified email fails closed — no principal."""
        # Arrange
        provider = StytchProvider(
            edition="ee",
            verifier=FakeStytchVerifier(
                {"no-email-token": StytchVerification(user_id="user-test-2", email=None)}
            ),
            user_repository=FakeUserRepository({}),
        )
        request = _request({"stytch_session": "no-email-token"})

        # Act / Assert
        assert await provider.authenticate(request) is None

    async def test_no_database_connection_returns_none(self) -> None:
        """Without a live database the mapping cannot be checked — fail closed."""
        # Arrange
        request = _request({"stytch_session_jwt": "good-token"}, db_connection=None)

        # Act / Assert
        assert await self._provider.authenticate(request) is None
