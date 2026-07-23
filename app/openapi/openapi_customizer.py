"""Injects the deployment's real security schemes into the OpenAPI document.

``docs/design/API_CONTRACT.md`` §1–2 defines exactly two ways a request can
carry credentials: the ``lavs_session`` HttpOnly browser cookie (minted by
``POST /auth/login``, or by ``POST /auth/stytch/callback`` in the EE edition —
Stytch is not a separate scheme) and the headless ``X-API-Key`` header. This
customizer declares both under ``components.securitySchemes`` and marks a
``security`` requirement on exactly the operations guarded by
:func:`~app.auth.require_principal.require_principal` — discovered by
inspecting each route's dependency tree, so the document stays honest as
routes come and go. Public bootstrap routes (``/health``, ``/ready``,
``/meta``, and the credential-establishing ``/auth`` flows) carry no marker.
"""

from typing import Any

from fastapi import FastAPI
from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute

from app.auth.require_principal import require_principal
from app.auth.session.session_cookie import SessionCookie
from app.security.api_key_settings import ApiKeySettings


class OpenApiCustomizer:
    """Adds security schemes and per-operation security markers to the schema.

    The fixed scheme names are held as class variables per project convention.
    ``apiKeyAuth`` and ``cookieAuth`` mirror the two auth modes the contract
    ships in v1; either satisfies a secured route, so both appear as
    alternatives in each secured operation's ``security`` list.
    """

    API_KEY_SCHEME_NAME: str = "apiKeyAuth"
    COOKIE_SCHEME_NAME: str = "cookieAuth"

    def customize(self, application: FastAPI) -> dict[str, Any]:
        """Build, mutate, and return the application's OpenAPI schema.

        Calls ``application.openapi()`` (which caches the generated schema on
        ``application.openapi_schema``) and mutates that cached document in
        place, so every later ``/openapi.json`` render includes the schemes.

        Args:
            application: The fully-routed FastAPI application.

        Returns:
            The customized OpenAPI schema.
        """
        schema = application.openapi()
        components = schema.setdefault("components", {})
        components["securitySchemes"] = self._security_schemes()
        self._mark_secured_operations(application, schema)
        return schema

    def _security_schemes(self) -> dict[str, dict[str, str]]:
        """Return the ``securitySchemes`` component matching the contract.

        The cookie name comes from :class:`SessionCookie` and the header name
        from :class:`ApiKeySettings` — the same single sources of truth the
        providers authenticate against — so the document cannot drift.

        Returns:
            The scheme definitions keyed by their component names.
        """
        return {
            self.API_KEY_SCHEME_NAME: {
                "type": "apiKey",
                "in": "header",
                "name": ApiKeySettings().header_name,
                "description": (
                    "Headless deploy credential for CI, pipelines, and "
                    "deploy-configured clients (`LAVS_AUTH_MODES=…,apikey`). "
                    "No cookie, no session."
                ),
            },
            self.COOKIE_SCHEME_NAME: {
                "type": "apiKey",
                "in": "cookie",
                "name": SessionCookie.NAME,
                "description": (
                    "HttpOnly browser session cookie set by `POST /auth/login`. "
                    "In the EE edition the same cookie is issued by "
                    "`POST /auth/stytch/callback` after the Stytch session JWT "
                    "is verified — the rest of the API is identical regardless "
                    "of how the principal was obtained."
                ),
            },
        }

    def _mark_secured_operations(self, application: FastAPI, schema: dict[str, Any]) -> None:
        """Set a ``security`` requirement on every principal-guarded operation.

        Routes without :func:`require_principal` in their dependency tree
        (the public bootstrap surface) are left unmarked, keeping ``/docs``
        accurate: no padlock appears on routes that need no credentials.

        Args:
            application: The application whose routes are inspected.
            schema: The OpenAPI schema to mutate in place.
        """
        paths = schema.get("paths", {})
        for route in application.routes:
            if not isinstance(route, APIRoute):
                continue
            if not self._requires_principal(route.dependant):
                continue
            path_item = paths.get(route.path, {})
            for method in route.methods:
                operation = path_item.get(method.lower())
                if operation is not None:
                    operation["security"] = [
                        {self.API_KEY_SCHEME_NAME: []},
                        {self.COOKIE_SCHEME_NAME: []},
                    ]

    def _requires_principal(self, dependant: Dependant) -> bool:
        """Report whether a dependency tree resolves the request principal.

        Args:
            dependant: The root of a route's resolved dependency tree.

        Returns:
            ``True`` when :func:`require_principal` appears anywhere in the
            tree (router-level ``dependencies=`` or a ``PrincipalDep``
            parameter), ``False`` otherwise.
        """
        if dependant.call is require_principal:
            return True
        return any(self._requires_principal(dependency) for dependency in dependant.dependencies)
