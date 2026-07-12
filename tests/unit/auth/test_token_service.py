"""Unit tests for :class:`TokenService`."""

from app.auth.token_service import TokenService


class TestTokenService:
    """Token generation, hashing, and constant-time comparison."""

    def test_generated_tokens_are_unique(self) -> None:
        """Successive tokens are high-entropy and distinct."""
        # Arrange
        service = TokenService()

        # Act
        first = service.generate_token()
        second = service.generate_token()

        # Assert
        assert first != second
        assert len(first) > 0

    def test_hash_is_deterministic_and_not_the_token(self) -> None:
        """The stored hash is the SHA-256 hex digest, never the raw token."""
        # Arrange
        service = TokenService()
        token = service.generate_token()

        # Act
        digest = service.hash_token(token)

        # Assert
        assert digest == service.hash_token(token)
        assert digest != token
        assert len(digest) == 64

    def test_compare_matches_only_the_right_token(self) -> None:
        """``compare`` is true for the token behind a hash, false otherwise."""
        # Arrange
        service = TokenService()
        token = service.generate_token()
        digest = service.hash_token(token)

        # Act / Assert
        assert service.compare(token, digest) is True
        assert service.compare("not-the-token", digest) is False
