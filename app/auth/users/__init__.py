"""Shared user persistence for the password-auth lanes.

Owned by the foundation because both the sign-up/verify lane (R1) and the
login/session lane (R2) read and write the ``users`` table. Password hashes are
persisted here but never surfaced in the response model.
"""
