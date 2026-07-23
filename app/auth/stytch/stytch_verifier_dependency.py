"""FastAPI dependency exposing the application-managed :class:`StytchVerifier`.

Mirrors :func:`app.mail.mailer_dependency.get_mailer`: the concrete verifier is
placed on ``app.state.stytch_verifier`` by the application lifespan (an
SDK-backed verifier when the ``stytch`` mode is enabled). When the app was
started without one — a bare ``TestClient``, or a deployment where stytch is
disabled — an SDK verifier is created lazily and stored on ``app.state``; with
no Stytch configuration it verifies nothing, so the callback keeps failing
closed. Tests inject a fake by assigning ``app.state.stytch_verifier``.
"""

from fastapi import Request

from app.auth.stytch.stytch_sdk_verifier import StytchSdkVerifier
from app.auth.stytch.stytch_verifier import StytchVerifier


def get_stytch_verifier(request: Request) -> StytchVerifier:
    """Return the application-managed Stytch verifier.

    Args:
        request: The incoming request, used to reach ``app.state``.

    Returns:
        The live :class:`StytchVerifier` managed by the application lifespan,
        or a lazily-created SDK verifier when none was installed.
    """
    state = request.app.state
    verifier = state.stytch_verifier if hasattr(state, "stytch_verifier") else None
    if verifier is None:
        verifier = StytchSdkVerifier()
        state.stytch_verifier = verifier
    return verifier
