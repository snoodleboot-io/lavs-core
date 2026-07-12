"""Pluggable authentication spine for LAVS.

Auth is selected by deployment config (``LAVS_AUTH_MODES``) and resolved to a
single :class:`~app.auth.principal.Principal` per request. Each enabled
:class:`~app.auth.auth_provider.AuthProvider` gets a chance to authenticate a
request; the first that succeeds wins. When no provider is configured the
resolver returns a permissive anonymous service principal so an unconfigured
deployment (and the test-suite default) stays open. See
``docs/design/API_CONTRACT.md`` §1–2 for the authority on the model and flows.
"""
