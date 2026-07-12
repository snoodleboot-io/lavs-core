"""Mail abstraction for the auth lanes.

A :class:`~app.mail.mailer.Mailer` sends transactional email (email-verification
tokens). The v1 pipeline ships :class:`~app.mail.capture_mailer.CaptureMailer`, an
in-memory sink that makes the verification flow deterministic and testable with
no SMTP daemon. A single instance lives on ``app.state.mailer``.
"""
