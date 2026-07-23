"""The identity a successful Stytch session verification resolves to."""

from pydantic import BaseModel


class StytchVerification(BaseModel):
    """The verified Stytch identity, decoupled from the SDK response shape.

    Carries only what LAVS needs to mint a principal and map the caller onto
    the shared ``users`` table: the Stytch user id and the (Stytch-verified)
    email. Keeping this a small local model means the provider, the callback
    route, and the tests never depend on the Stytch SDK's own types.
    """

    user_id: str
    email: str | None = None
