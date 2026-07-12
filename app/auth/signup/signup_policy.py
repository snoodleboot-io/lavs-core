"""Fixed sign-up input policy (email shape and password strength).

Centralises the sign-up validation constants in one named place rather than
scattering magic literals across the request model, so the pattern and the
minimum password length live in exactly one location.
"""


class SignupPolicy:
    """Named constants governing sign-up input validation."""

    MIN_PASSWORD_LENGTH: int = 12
    """Minimum accepted plaintext password length (characters)."""

    EMAIL_PATTERN: str = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    """A deliberately conservative ``local@domain.tld`` shape check.

    Full RFC-5322 validation would require the ``email-validator`` dependency
    (not installed); this rejects the obviously malformed while normalisation
    lower-cases the value so the domain allow-list check is case-insensitive.
    """
