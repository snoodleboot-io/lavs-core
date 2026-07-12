"""Unit tests for :class:`PasswordHasher` (argon2id)."""

from app.auth.password_hasher import PasswordHasher


class TestPasswordHasher:
    """Hashing never leaks plaintext; verification is correct."""

    def test_hash_is_not_plaintext(self) -> None:
        """The hash must not be (or contain) the plaintext password."""
        # Arrange
        hasher = PasswordHasher()
        password = "correct horse battery staple"

        # Act
        digest = hasher.hash_password(password)

        # Assert
        assert digest != password
        assert password not in digest
        assert digest.startswith("$argon2id$")

    def test_verify_accepts_correct_password(self) -> None:
        """A matching password verifies true."""
        # Arrange
        hasher = PasswordHasher()
        digest = hasher.hash_password("s3cret-pass")

        # Act / Assert
        assert hasher.verify_password(digest, "s3cret-pass") is True

    def test_verify_rejects_wrong_password(self) -> None:
        """A wrong password verifies false (no exception surfaces)."""
        # Arrange
        hasher = PasswordHasher()
        digest = hasher.hash_password("s3cret-pass")

        # Act / Assert
        assert hasher.verify_password(digest, "wrong-pass") is False

    def test_hashes_are_salted(self) -> None:
        """Hashing the same password twice yields different digests (salt)."""
        # Arrange
        hasher = PasswordHasher()

        # Act
        first = hasher.hash_password("same")
        second = hasher.hash_password("same")

        # Assert
        assert first != second
