"""The typed context handed to every discovered LAVS plugin.

A plugin is any callable ``(PluginContext) -> None`` published by an external
package under the ``lavs.plugins`` entry-point group (see
:mod:`app.plugins.plugin_loader`). Core (``lavs-core``) imports **no** plugin
code — discovery is by entry point at application startup — so the OSS build
carries no plugin dependency and behaves identically when nothing is installed.

The context is the one seam a plugin extends the running application through.
It deliberately exposes only the four capabilities a downstream edition (for
example a private managed-identity EE package) needs, and nothing more:

* :attr:`auth_registry` — register an
  :class:`~app.auth.auth_provider.AuthProvider` so the resolver authenticates
  the plugin's credential. The resolver reads the registry live, so a provider
  registered here at startup takes effect for every subsequent request.
* :attr:`auth_settings` — read the deployment's ``LAVS_AUTH_*`` configuration.
* :meth:`add_meta_extension` — contribute fields to the public ``GET /meta``
  capability descriptor (see the :data:`MetaExtension` contract below).
* :attr:`app` — the live :class:`~fastapi.FastAPI` application, so a plugin can
  mount its own routers via ``context.app.include_router(...)``.
"""

from collections.abc import Callable

from fastapi import FastAPI

from app.auth.auth_registry import AuthRegistry
from app.auth.auth_settings import AuthSettings

type MetaExtension = Callable[[AuthSettings], dict[str, object]]
"""A ``/meta`` contributor.

Called with the deployment :class:`AuthSettings` each time ``GET /meta`` is
served; its returned mapping is merged into the response body on top of the
base OSS fields (``edition``, ``auth_modes``). Later extensions win on a key
clash. Returning an empty mapping contributes nothing.
"""


class PluginContext:
    """The extension surface handed to each plugin at application startup.

    Constructed once in the application lifespan after core wiring completes
    (see :func:`app.plugins.plugin_loader.load_plugins`). The ``meta_extensions``
    list is the same object stored on ``app.state.meta_extensions`` that the
    ``/meta`` route reads, so a plugin's :meth:`add_meta_extension` call is
    observed by every later request without any further wiring.
    """

    def __init__(
        self,
        app: FastAPI,
        auth_registry: AuthRegistry,
        auth_settings: AuthSettings,
        meta_extensions: list[MetaExtension],
    ) -> None:
        """Initialise the context.

        Args:
            app: The live FastAPI application (for router mounting).
            auth_registry: The live provider registry (the resolver reads it
                live, so a provider registered here takes effect immediately).
            auth_settings: The deployment auth settings.
            meta_extensions: The shared, mutable list of ``/meta`` contributors
                (the same object exposed on ``app.state.meta_extensions``).
        """
        self._app = app
        self._auth_registry = auth_registry
        self._auth_settings = auth_settings
        self._meta_extensions = meta_extensions

    @property
    def app(self) -> FastAPI:
        """Return the live FastAPI application for router contribution."""
        return self._app

    @property
    def auth_registry(self) -> AuthRegistry:
        """Return the live provider registry a plugin registers onto."""
        return self._auth_registry

    @property
    def auth_settings(self) -> AuthSettings:
        """Return the deployment auth settings a plugin reads its config from."""
        return self._auth_settings

    def add_meta_extension(self, extension: MetaExtension) -> None:
        """Register a contributor to the public ``GET /meta`` response.

        Args:
            extension: A ``(AuthSettings) -> dict[str, object]`` callable whose
                output is merged into the ``/meta`` body on top of the base
                fields (see :data:`MetaExtension`).
        """
        self._meta_extensions.append(extension)
