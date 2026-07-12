"""The mail-sending abstraction the auth lanes depend on."""

from abc import ABC, abstractmethod


class Mailer(ABC):
    """Sends a transactional email.

    Kept deliberately minimal so backends (in-memory capture now, SMTP/provider
    later) are interchangeable behind the same contract. Resource and auth lanes
    depend on this abstraction, not a concrete transport.
    """

    @abstractmethod
    def send(self, to: str, subject: str, body: str) -> None:
        """Send an email.

        Args:
            to: The recipient address.
            subject: The email subject line.
            body: The email body.
        """
        raise NotImplementedError
