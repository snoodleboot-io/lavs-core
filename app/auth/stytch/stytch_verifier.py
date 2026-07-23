"""Interface for verifying a Stytch session token or session JWT."""

from app.auth.stytch.stytch_verification import StytchVerification


class StytchVerifier:
    """Interface every Stytch session verifier implements.

    The seam between LAVS and the Stytch SDK: production wires the
    SDK-backed :class:`~app.auth.stytch.stytch_sdk_verifier.StytchSdkVerifier`,
    while tests inject a fake so no network is ever touched. A verifier maps a
    presented token to a :class:`StytchVerification` on success and ``None`` on
    **any** failure — it never raises for an invalid credential, mirroring the
    provider contract in :class:`~app.auth.auth_provider.AuthProvider`.
    """

    async def verify(self, token: str) -> StytchVerification | None:
        """Verify a Stytch session token or session JWT.

        Args:
            token: The raw Stytch session token or session JWT to verify.

        Returns:
            The verified identity, or ``None`` when the token is invalid,
            expired, or verification is not possible.
        """
        raise NotImplementedError(f"{self.__class__.__name__} must implement verify()")
