"""Router for the ``/auth`` resource.

Carries the prefix and tag; the password-auth lanes add the routes (R1:
``/auth/signup`` + ``/auth/verify``; R2: ``/auth/login`` + ``/auth/logout`` +
``/auth/me``). See ``docs/design/API_CONTRACT.md`` §2.

Critically, this router does **not** declare a router-level ``require_principal``
dependency: the auth routes establish a principal, so they must be reachable
without one already present. ``/auth/me`` enforces authentication itself via a
per-route dependency.

Security posture of the login lane:

* Failures are **generic** — a wrong password, an unknown email, and an
  unverified/disabled account all return the same ``401 invalid credentials``,
  so a response never reveals whether an account exists or its status (no user
  enumeration).
* The password check runs even when no user matched (against a throwaway hash),
  so the request cannot be enumerated by timing either.
* The session token is high-entropy, stored only as its hash with a TTL, and
  the cookie is ``HttpOnly``/``Secure``/``SameSite=Lax``.
"""

import secrets
from typing import Annotated

import duckdb
from fastapi import APIRouter, Depends, Request, Response, status

from app.auth.auth_settings import AuthSettings
from app.auth.password_hasher import PasswordHasher
from app.auth.require_principal import PrincipalDep
from app.auth.session.session_cookie import SessionCookie
from app.auth.session.session_service import SessionService
from app.auth.signup.signup_service import SignupService
from app.auth.signup.verification_service import VerificationService
from app.auth.users.user_repository import UserRepository
from app.auth.users.user_status import UserStatus
from app.connections.db_dependency import get_db_connection
from app.errors.unauthorized_error import UnauthorizedError
from app.mail.mailer import Mailer
from app.mail.mailer_dependency import get_mailer
from app.models.requests.login_model import LoginModel
from app.models.requests.signup_model import SignupModel
from app.models.requests.verify_model import VerifyModel
from app.models.responses.signup_accepted_model import SignupAcceptedModel
from app.models.responses.user_response_model import UserResponseModel

router = APIRouter(tags=["auth"], prefix="/auth")

DbConnection = Annotated[duckdb.DuckDBPyConnection, Depends(get_db_connection)]
MailerDep = Annotated[Mailer, Depends(get_mailer)]

_GENERIC_LOGIN_FAILURE = "invalid credentials"

# A throwaway argon2 hash used to equalise timing when no user matched, so the
# presence of an account cannot be inferred from how long a login takes. Minted
# once at import over a random secret; it can never match a real password.
_TIMING_EQUALISER_HASH = PasswordHasher().hash_password(secrets.token_urlsafe(32))


def _auth_settings(request: Request) -> AuthSettings:
    """Return the application-managed :class:`AuthSettings`.

    Prefers the settings installed on ``app.state`` by the lifespan; falls back
    to an environment-built instance when the app was started without one (for
    example a bare ``TestClient``), mirroring :func:`require_principal`.

    Args:
        request: The incoming request.

    Returns:
        The auth settings to apply to this request.
    """
    state = request.app.state
    settings = state.auth_settings if hasattr(state, "auth_settings") else None
    return settings if settings is not None else AuthSettings()


@router.post(
    "/signup",
    response_model=SignupAcceptedModel,
    status_code=status.HTTP_202_ACCEPTED,
)
async def signup(
    body: SignupModel,
    conn: DbConnection,
    mailer: MailerDep,
    request: Request,
) -> SignupAcceptedModel:
    """Register a pending user and email them a verification token.

    Args:
        body: The sign-up request body (``email`` + ``password``).
        conn: The application-managed DuckDB connection.
        mailer: The application-managed mailer delivering the raw token.
        request: The incoming request, used to reach the auth settings.

    Returns:
        A 202 acknowledgement with ``pending_verification`` status.

    Raises:
        DomainNotAllowedError: When the email's domain is not allow-listed (403).
        ConflictError: When the email is already registered (409).
    """
    await SignupService().register(
        conn=conn, mailer=mailer, model=body, settings=_auth_settings(request)
    )
    return SignupAcceptedModel()


@router.post("/verify", response_model=UserResponseModel)
async def verify(
    body: VerifyModel,
    conn: DbConnection,
) -> UserResponseModel:
    """Verify an email token, activating the corresponding user.

    Args:
        body: The verify request body carrying the raw token.
        conn: The application-managed DuckDB connection.

    Returns:
        The activated user as a safe :class:`UserResponseModel`.

    Raises:
        NotFoundError: When the token is unknown, expired, or already used (a
            single generic failure — no enumeration).
    """
    return await VerificationService().verify(conn=conn, model=body)


@router.post("/login", response_model=UserResponseModel)
async def login(
    body: LoginModel,
    request: Request,
    response: Response,
    conn: DbConnection,
) -> UserResponseModel:
    """Authenticate a user and open a session.

    Verifies the password against the stored argon2 hash and requires an
    ``active`` account. On success a fresh session is created — its token stored
    only as a hash with a TTL — and the raw token is set as the ``lavs_session``
    cookie. On **any** failure a single generic 401 is returned.

    Args:
        body: The login request body (``email`` and ``password``).
        request: The incoming request, used to read the deployment settings.
        response: The outgoing response, used to set the session cookie.
        conn: The application-managed DuckDB connection.

    Returns:
        The authenticated user as a safe :class:`UserResponseModel`.

    Raises:
        UnauthorizedError: On unknown email, wrong password, or a non-active
            account — always with the same generic message.
    """
    user_row = await UserRepository().get_user_by_email(conn, body.email)
    stored_hash = str(user_row[2]) if user_row is not None else _TIMING_EQUALISER_HASH

    password_ok = PasswordHasher().verify_password(stored_hash, body.password)

    if user_row is None or not password_ok or str(user_row[3]) != UserStatus.ACTIVE.value:
        raise UnauthorizedError(message=_GENERIC_LOGIN_FAILURE)

    settings = _auth_settings(request)
    ttl_seconds = settings.session_ttl_seconds()
    token = SessionService().create_session(conn, user_id=str(user_row[0]), ttl_seconds=ttl_seconds)

    response.set_cookie(
        key=SessionCookie.NAME,
        value=token,
        max_age=ttl_seconds,
        httponly=SessionCookie.HTTP_ONLY,
        secure=SessionCookie.SECURE,
        samesite=SessionCookie.SAME_SITE,
        path=SessionCookie.PATH,
    )

    return UserResponseModel(
        id=str(user_row[0]),
        email=str(user_row[1]),
        status=str(user_row[3]),
        edition=None if user_row[4] is None else str(user_row[4]),
    )


@router.get("/me", response_model=UserResponseModel)
async def me(conn: DbConnection, principal: PrincipalDep) -> UserResponseModel:
    """Return the currently authenticated caller.

    Resolves the request's principal (a user via the session cookie, or any
    other configured provider) and returns its user projection. An
    unauthenticated request is rejected with 401 by ``require_principal`` before
    this handler runs.

    Args:
        conn: The application-managed DuckDB connection.
        principal: The resolved principal (injected by ``require_principal``).

    Returns:
        The caller as a :class:`UserResponseModel`.
    """
    user_row = await UserRepository().get_user_by_id(conn, principal.id)
    if user_row is not None:
        return UserResponseModel(
            id=str(user_row[0]),
            email=str(user_row[1]),
            status=str(user_row[3]),
            edition=None if user_row[4] is None else str(user_row[4]),
        )

    return UserResponseModel(
        id=principal.id,
        email=principal.email if principal.email is not None else principal.id,
        status=UserStatus.ACTIVE.value,
        edition=principal.edition,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: Request, conn: DbConnection) -> Response:
    """Revoke the current session and clear the session cookie.

    Idempotent: a request without a session cookie still succeeds. The matching
    session row (if any) is deleted and the cookie is cleared.

    Args:
        request: The incoming request, used to read the session cookie.
        conn: The application-managed DuckDB connection.

    Returns:
        An empty ``204 No Content`` response that clears the cookie.
    """
    token = request.cookies.get(SessionCookie.NAME)
    if token is not None and token != "":
        SessionService().delete_session(conn, token)

    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(
        key=SessionCookie.NAME,
        path=SessionCookie.PATH,
        httponly=SessionCookie.HTTP_ONLY,
        secure=SessionCookie.SECURE,
        samesite=SessionCookie.SAME_SITE,
    )
    return response
