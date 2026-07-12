"""FastAPI dependency exposing the application-managed :class:`Mailer`.

Mirrors :func:`app.connections.db_dependency.get_db_connection`: the concrete
mailer is placed on ``app.state.mailer`` by the application lifespan. When the
app was started without a lifespan (for example a bare ``TestClient``), a
:class:`~app.mail.capture_mailer.CaptureMailer` is created lazily and stored on
``app.state`` so it persists across requests and remains inspectable — this
keeps the sign-up/verify flow drivable without an SMTP daemon.
"""

from fastapi import Request

from app.mail.capture_mailer import CaptureMailer
from app.mail.mailer import Mailer


def get_mailer(request: Request) -> Mailer:
    """Return the application-managed mailer.

    Args:
        request: The incoming request, used to reach ``app.state``.

    Returns:
        The live :class:`Mailer` managed by the application lifespan, or a
        lazily-created capture mailer when none was installed.
    """
    state = request.app.state
    mailer = state.mailer if hasattr(state, "mailer") else None
    if mailer is None:
        mailer = CaptureMailer()
        state.mailer = mailer
    return mailer
