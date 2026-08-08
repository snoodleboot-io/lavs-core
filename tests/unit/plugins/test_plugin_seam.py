"""Contract test for the ``lavs.plugins`` extension seam.

Proves that a FAKE in-process plugin — a plain ``(PluginContext) -> None``
callable, with no reference to any specific out-of-core edition — can, through
the context alone: register an :class:`AuthProvider`, contribute a field to
``GET /meta``, and mount its own router. The seam is exactly what an external
private package will consume to re-add an edition without core importing it, so
this file is the executable definition of that boundary.
"""

from importlib.metadata import EntryPoint

import pytest
from fastapi import APIRouter, FastAPI, Request
from fastapi.testclient import TestClient

from app.auth.auth_provider import AuthProvider
from app.auth.auth_registry import AuthRegistry
from app.auth.auth_settings import AuthSettings
from app.auth.principal import Principal
from app.plugins import plugin_loader
from app.plugins.plugin_context import MetaExtension, PluginContext
from app.plugins.plugin_loader import load_plugins
from app.routers import meta


class _FakeProvider(AuthProvider):
    """A no-op provider standing in for an edition's real credential provider."""

    async def authenticate(self, request: Request) -> Principal | None:
        """Recognise nothing; the registration itself is what the test asserts."""
        return None


def _fake_meta_extension(settings: AuthSettings) -> dict[str, object]:
    """Contribute two extra ``/meta`` fields, one echoing live settings."""
    return {"fake_capability": True, "fake_edition_echo": settings.edition()}


_fake_router = APIRouter()


@_fake_router.get("/_fake_plugin/ping")
def _fake_ping() -> dict[str, str]:
    """A route mounted by the fake plugin to prove router contribution."""
    return {"pong": "ok"}


def _fake_plugin(context: PluginContext) -> None:
    """The fake plugin entry point: exercises all three seam capabilities."""
    context.auth_registry.register(_FakeProvider())
    context.add_meta_extension(_fake_meta_extension)
    context.app.include_router(_fake_router)


def _broken_plugin(context: PluginContext) -> None:
    """A plugin that raises during registration (isolation test)."""
    raise RuntimeError("boom")


class _FakeEntryPoint:
    """A minimal stand-in for :class:`importlib.metadata.EntryPoint`."""

    def __init__(self, name: str, plugin: object) -> None:
        self.name = name
        self._plugin = plugin

    def load(self) -> object:
        """Return the plugin callable, mirroring ``EntryPoint.load``."""
        return self._plugin


def _make_context() -> tuple[PluginContext, FastAPI, AuthRegistry, list[object]]:
    """Build a PluginContext over throwaway wiring (no global app pollution)."""
    app = FastAPI()
    registry = AuthRegistry()
    settings = AuthSettings(edition="oss")
    extensions: list[MetaExtension] = []
    context = PluginContext(
        app=app,
        auth_registry=registry,
        auth_settings=settings,
        meta_extensions=extensions,
    )
    return context, app, registry, extensions


class TestPluginContext:
    """The context exposes exactly the four documented capabilities."""

    def test_exposes_app_registry_and_settings(self) -> None:
        """The context surfaces the app, registry, and settings it was built with."""
        # Arrange
        context, app, registry, _ = _make_context()

        # Act / Assert
        assert context.app is app
        assert context.auth_registry is registry
        assert context.auth_settings.edition() == "oss"

    def test_add_meta_extension_appends_to_shared_list(self) -> None:
        """``add_meta_extension`` mutates the same list the route reads."""
        # Arrange
        context, _, _, extensions = _make_context()

        # Act
        context.add_meta_extension(_fake_meta_extension)

        # Assert
        assert extensions == [_fake_meta_extension]


class TestLoadPlugins:
    """``load_plugins`` discovers ``lavs.plugins`` entry points and invokes them."""

    def test_no_entry_points_is_a_clean_noop(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """With nothing installed the loader touches nothing and does not raise."""
        # Arrange
        context, app, registry, extensions = _make_context()
        monkeypatch.setattr(plugin_loader, "entry_points", lambda group: [])

        # Act
        load_plugins(context)

        # Assert
        assert registry.is_empty()
        assert extensions == []
        assert "/_fake_plugin/ping" not in {route.path for route in app.routes}

    def test_discovers_and_wires_a_fake_plugin(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A discovered plugin registers a provider, a /meta field, and a route."""
        # Arrange
        context, app, registry, extensions = _make_context()
        monkeypatch.setattr(
            plugin_loader,
            "entry_points",
            lambda group: [_FakeEntryPoint("fake", _fake_plugin)],
        )

        # Act
        load_plugins(context)

        # Assert — all three capabilities took effect through the context alone
        providers = registry.providers()
        assert len(providers) == 1
        assert isinstance(providers[0], _FakeProvider)
        assert extensions == [_fake_meta_extension]
        assert "/_fake_plugin/ping" in {route.path for route in app.routes}

    def test_queries_the_lavs_plugins_group(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The loader asks for exactly the ``lavs.plugins`` entry-point group."""
        # Arrange
        context, _, _, _ = _make_context()
        seen: dict[str, str] = {}

        def _record(group: str) -> list[EntryPoint]:
            seen["group"] = group
            return []

        monkeypatch.setattr(plugin_loader, "entry_points", _record)

        # Act
        load_plugins(context)

        # Assert
        assert seen["group"] == "lavs.plugins"

    def test_a_broken_plugin_is_isolated(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A plugin that raises is logged and skipped, never crashing startup."""
        # Arrange
        context, _, registry, _ = _make_context()
        monkeypatch.setattr(
            plugin_loader,
            "entry_points",
            lambda group: [_FakeEntryPoint("broken", _broken_plugin)],
        )

        # Act — must not raise
        load_plugins(context)

        # Assert
        assert registry.is_empty()


class TestMetaExtensionContract:
    """The ``/meta`` route merges plugin fields on top of the OSS base body."""

    def _client(self, extensions: list[object] | None) -> TestClient:
        """A TestClient over a throwaway app carrying only the meta router."""
        app = FastAPI()
        app.include_router(meta.router)
        app.state.auth_settings = AuthSettings(edition="oss", modes=set())
        if extensions is not None:
            app.state.meta_extensions = extensions
        return TestClient(app)

    def test_body_is_byte_identical_without_extensions(self) -> None:
        """With no extension registered the body is the base OSS shape only."""
        # Arrange
        client = self._client(extensions=[])

        # Act
        body = client.get("/meta").json()

        # Assert
        assert body == {"edition": "oss", "auth_modes": []}

    def test_extension_fields_merge_into_the_response(self) -> None:
        """A registered extension's fields appear alongside the base fields."""
        # Arrange
        client = self._client(extensions=[_fake_meta_extension])

        # Act
        body = client.get("/meta").json()

        # Assert — base fields preserved, plugin fields added
        assert body["edition"] == "oss"
        assert body["auth_modes"] == []
        assert body["fake_capability"] is True
        assert body["fake_edition_echo"] == "oss"
