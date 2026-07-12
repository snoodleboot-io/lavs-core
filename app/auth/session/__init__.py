"""Password-session support: cookie configuration and the session store.

Owned by the R2 login lane. Sessions are opaque, high-entropy tokens minted by
:class:`~app.auth.token_service.TokenService`, handed to the client once, and
persisted **only** as their SHA-256 hash with a TTL expiry — a database leak
therefore never yields a usable session token.
"""
