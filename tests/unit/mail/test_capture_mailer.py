"""Unit tests for :class:`CaptureMailer`."""

from app.mail.capture_mailer import CaptureMailer
from app.mail.captured_email import CapturedEmail


class TestCaptureMailer:
    """In-memory capture of sent messages."""

    def test_send_records_message(self) -> None:
        """A sent message is captured with all fields."""
        # Arrange
        mailer = CaptureMailer()

        # Act
        mailer.send(to="user@example.com", subject="Verify", body="token=abc")

        # Assert
        assert mailer.messages() == (
            CapturedEmail(to="user@example.com", subject="Verify", body="token=abc"),
        )

    def test_last_message_returns_most_recent(self) -> None:
        """``last_message`` returns the newest capture, or None when empty."""
        # Arrange
        mailer = CaptureMailer()
        assert mailer.last_message() is None

        # Act
        mailer.send(to="a@example.com", subject="One", body="1")
        mailer.send(to="b@example.com", subject="Two", body="2")

        # Assert
        last = mailer.last_message()
        assert last is not None
        assert last.subject == "Two"

    def test_last_for_filters_by_recipient(self) -> None:
        """``last_for`` returns the newest message for a specific recipient."""
        # Arrange
        mailer = CaptureMailer()
        mailer.send(to="a@example.com", subject="First", body="1")
        mailer.send(to="b@example.com", subject="Other", body="2")
        mailer.send(to="a@example.com", subject="Second", body="3")

        # Act
        result = mailer.last_for("a@example.com")

        # Assert
        assert result is not None
        assert result.subject == "Second"
        assert mailer.last_for("missing@example.com") is None

    def test_clear_empties_the_buffer(self) -> None:
        """``clear`` discards all captured messages."""
        # Arrange
        mailer = CaptureMailer()
        mailer.send(to="a@example.com", subject="One", body="1")

        # Act
        mailer.clear()

        # Assert
        assert mailer.messages() == ()
