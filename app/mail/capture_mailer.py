"""An in-memory :class:`~app.mail.mailer.Mailer` that records sent messages."""

from app.mail.captured_email import CapturedEmail
from app.mail.mailer import Mailer


class CaptureMailer(Mailer):
    """A deterministic mail sink that stores sent messages in memory.

    This is the v1 email transport: instead of talking to an SMTP daemon it
    appends every send to an in-memory list, so the sign-up/verify flow can be
    driven end to end (retrieve the verification token straight from the last
    captured message). A single instance is app-scoped on ``app.state.mailer``.
    """

    def __init__(self) -> None:
        """Initialise an empty capture buffer."""
        self._messages: list[CapturedEmail] = []

    def send(self, to: str, subject: str, body: str) -> None:
        """Record an email in the in-memory buffer.

        Args:
            to: The recipient address.
            subject: The email subject line.
            body: The email body.
        """
        self._messages.append(CapturedEmail(to=to, subject=subject, body=body))

    def messages(self) -> tuple[CapturedEmail, ...]:
        """Return every captured message in send order."""
        return tuple(self._messages)

    def last_message(self) -> CapturedEmail | None:
        """Return the most recently captured message, or ``None`` when empty."""
        return self._messages[-1] if self._messages else None

    def last_for(self, recipient: str) -> CapturedEmail | None:
        """Return the most recent message sent to a recipient.

        Args:
            recipient: The recipient address to search for.

        Returns:
            The latest :class:`CapturedEmail` addressed to ``recipient``, or
            ``None`` when none was sent.
        """
        for message in reversed(self._messages):
            if message.to == recipient:
                return message
        return None

    def clear(self) -> None:
        """Discard all captured messages."""
        self._messages.clear()
