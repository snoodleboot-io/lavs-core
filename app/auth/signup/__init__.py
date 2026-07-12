"""Password sign-up and email-verification lane (R1).

Owns the ``POST /auth/signup`` and ``POST /auth/verify`` flows: domain
allow-list enforcement, duplicate-email conflict handling, argon2id password
hashing, and the issue/consume lifecycle of single-use, hashed, expiring email
verification tokens. See ``docs/design/API_CONTRACT.md`` §2.
"""
