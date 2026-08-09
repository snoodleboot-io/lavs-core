"""An in-memory :class:`~app.mail.mailer.Mailer` that records sent messages."""

from collections import deque

from app.mail.captured_email import CapturedEmail
from app.mail.mailer import Mailer


class CaptureMailer(Mailer):
    """A deterministic mail sink that stores sent messages in memory.

    This is the v1 email transport: instead of talking to an SMTP daemon it
    appends every send to an in-memory buffer, so the sign-up/verify flow can
    be driven end to end (retrieve the verification token straight from the
    last captured message). A single instance is app-scoped on
    ``app.state.mailer``.

    Memory bound: the buffer is a ring capped at ``max_messages`` entries
    (100 by default) — when full, each new send silently evicts the oldest
    capture, so a long-lived process can never grow the buffer without bound.
    The read API (:meth:`messages`, :meth:`last_message`, :meth:`last_for`,
    :meth:`clear`) is unchanged.
    """

    _DEFAULT_MAX_MESSAGES: int = 100

    def __init__(self, max_messages: int | None = None) -> None:
        """Initialise an empty, bounded capture buffer.

        Args:
            max_messages: Ring-buffer capacity; the class default (100) when
                omitted.
        """
        capacity = max_messages if max_messages is not None else self._DEFAULT_MAX_MESSAGES
        self._messages: deque[CapturedEmail] = deque(maxlen=capacity)

    def send(self, to: str, subject: str, body: str) -> None:
        """Record an email in the in-memory ring buffer.

        When the buffer is at capacity the oldest capture is evicted.

        Args:
            to: The recipient address.
            subject: The email subject line.
            body: The email body.
        """
        self._messages.append(CapturedEmail(to=to, subject=subject, body=body))

    def messages(self) -> tuple[CapturedEmail, ...]:
        """Return every retained message in send order (oldest first)."""
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
            ``None`` when none was sent (or it has been evicted by the ring).
        """
        for message in reversed(self._messages):
            if message.to == recipient:
                return message
        return None

    def clear(self) -> None:
        """Discard all captured messages."""
        self._messages.clear()
