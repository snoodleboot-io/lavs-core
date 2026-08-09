"""Typed domain errors and the uniform error-envelope serialization.

The API contract (``docs/design/API_CONTRACT.md`` §3) mandates a single error
shape for every failure::

    {"error": {"code": "...", "message": "...", "details": {...}}}

Resource lanes raise the typed exceptions defined here; the handlers registered
by :func:`app.errors.handlers.register_error_handlers` translate them — and the
framework's own validation/HTTP errors — into that envelope.
"""
