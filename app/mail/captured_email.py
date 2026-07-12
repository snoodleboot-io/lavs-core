"""A single email captured by the in-memory mailer."""

from pydantic import BaseModel


class CapturedEmail(BaseModel):
    """An email recorded by :class:`~app.mail.capture_mailer.CaptureMailer`.

    Intentionally carries no timestamp: the capture sink is a deterministic test
    double, and minting a wall-clock time here would introduce non-determinism
    (and there is no request/DB clock to borrow at send time).
    """

    to: str
    subject: str
    body: str
