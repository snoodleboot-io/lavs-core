"""Builds the transactional email carrying a raw verification token.

The template lives here (one named place) so the subject/body copy is not a
magic literal embedded in the sign-up service. Only the **raw** token is placed
in the body; its hash is what the database stores.
"""


class VerificationEmail:
    """Renders the subject and body of a verification email for a token."""

    _SUBJECT: str = "Verify your LAVS account"
    _BODY_TEMPLATE: str = (
        "Welcome to LAVS.\n\n"
        "Use the following single-use token to verify your account:\n\n"
        "{token}\n\n"
        "The token expires; if it has, request a new one by signing up again."
    )

    def subject(self) -> str:
        """Return the verification email subject line."""
        return self._SUBJECT

    def body(self, token: str) -> str:
        """Return the verification email body embedding the raw token.

        Args:
            token: The raw (unhashed) verification token to deliver.

        Returns:
            The rendered plain-text email body.
        """
        return self._BODY_TEMPLATE.format(token=token)
