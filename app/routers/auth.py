"""Router shell for the ``/auth`` resource.

A deliberate shell carrying only the prefix and tag — the password-auth lanes
add the routes (R1: ``/auth/signup`` + ``/auth/verify``; R2: ``/auth/login`` +
``/auth/logout`` + ``/auth/me``). See ``docs/design/API_CONTRACT.md`` §2.

Critically, this router does **not** declare the ``require_principal``
dependency: the auth routes establish a principal, so they must be reachable
without one already present. (``/auth/me`` enforces authentication itself.)
"""

from typing import Annotated

import duckdb
from fastapi import APIRouter, Depends, Request, status

from app.auth.auth_settings import AuthSettings
from app.auth.signup.signup_service import SignupService
from app.auth.signup.verification_service import VerificationService
from app.connections.db_dependency import get_db_connection
from app.mail.mailer import Mailer
from app.mail.mailer_dependency import get_mailer
from app.models.requests.signup_model import SignupModel
from app.models.requests.verify_model import VerifyModel
from app.models.responses.signup_accepted_model import SignupAcceptedModel
from app.models.responses.user_response_model import UserResponseModel

router = APIRouter(tags=["auth"], prefix="/auth")

DbConnection = Annotated[duckdb.DuckDBPyConnection, Depends(get_db_connection)]
MailerDep = Annotated[Mailer, Depends(get_mailer)]


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
