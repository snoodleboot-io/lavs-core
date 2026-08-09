"""High-entropy token generation, hashing, and constant-time comparison.

Session and email-verification tokens are minted with :mod:`secrets` and are
**only ever stored hashed** (SHA-256 hex): the raw token is handed to the client
once and never persisted, so a database leak cannot yield a usable token.
Lookups compare the SHA-256 of a presented token against the stored hash with
:func:`hmac.compare_digest` so verification is constant-time.
"""

import hashlib
import hmac
import secrets


class TokenService:
    """Mint, hash, and compare opaque high-entropy tokens."""

    _DEFAULT_ENTROPY_BYTES: int = 32

    def __init__(self, entropy_bytes: int | None = None) -> None:
        """Initialise the service.

        Args:
            entropy_bytes: Number of random bytes backing each generated token.
                Defaults to 32 (256 bits) of entropy.
        """
        self._entropy_bytes = (
            entropy_bytes if entropy_bytes is not None else self._DEFAULT_ENTROPY_BYTES
        )

    def generate_token(self) -> str:
        """Generate a fresh URL-safe, high-entropy token.

        Returns:
            A cryptographically random token string (the raw secret — store only
            its :meth:`hash_token`).
        """
        return secrets.token_urlsafe(self._entropy_bytes)

    def hash_token(self, token: str) -> str:
        """Return the SHA-256 hex digest of a token (the stored form).

        Args:
            token: The raw token.

        Returns:
            The 64-character hex SHA-256 digest.
        """
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def compare(self, token: str, token_hash: str) -> bool:
        """Constant-time check that a raw token hashes to a stored digest.

        Args:
            token: The raw token presented by the client.
            token_hash: The stored SHA-256 hex digest to compare against.

        Returns:
            ``True`` when the token matches the stored hash.
        """
        return hmac.compare_digest(self.hash_token(token), token_hash)
