"""Argon2id password hashing and verification.

Wraps :class:`argon2.PasswordHasher`, which uses the ``argon2id`` variant by
default — the memory-hard, side-channel-resistant algorithm mandated by the
project's security invariants. Plaintext passwords are never stored: only the
self-describing argon2 hash string (which embeds its own salt and parameters) is
persisted, and verification is constant-time within the argon2 implementation.
The cost parameters are argon2's vetted defaults rather than bare local
constants.
"""

from argon2 import PasswordHasher as Argon2PasswordHasher
from argon2.exceptions import VerifyMismatchError


class PasswordHasher:
    """Hash and verify passwords with argon2id."""

    def __init__(self, hasher: Argon2PasswordHasher | None = None) -> None:
        """Initialise the hasher.

        Args:
            hasher: An optional pre-configured argon2 hasher. Defaults to a
                fresh :class:`argon2.PasswordHasher` using argon2's vetted
                default cost parameters.
        """
        self._hasher = hasher if hasher is not None else Argon2PasswordHasher()

    def hash_password(self, password: str) -> str:
        """Hash a plaintext password.

        Args:
            password: The plaintext password.

        Returns:
            The self-describing argon2id hash string (salt + parameters
            embedded). Never the plaintext.
        """
        return self._hasher.hash(password)

    def verify_password(self, password_hash: str, password: str) -> bool:
        """Verify a plaintext password against a stored argon2 hash.

        Args:
            password_hash: The stored argon2id hash string.
            password: The plaintext password to check.

        Returns:
            ``True`` when the password matches, ``False`` on mismatch.
        """
        try:
            return self._hasher.verify(password_hash, password)
        except VerifyMismatchError:
            return False
