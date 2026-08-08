"""Discovers and invokes LAVS plugins published under ``lavs.plugins``.

The seam that lets a private edition (for example a managed-identity EE package)
extend ``lavs-core`` without core importing any of its code. Each installed
distribution that ships a ``lavs.plugins`` entry point exposes a callable
``(PluginContext) -> None``; :func:`load_plugins` discovers those entry points
at application startup and invokes each with the shared
:class:`~app.plugins.plugin_context.PluginContext`.

Loading is best-effort and isolated: a plugin that fails to import or raises
during registration is logged with context and skipped, so a broken third-party
plugin can never take the core application down. When no plugin is installed the
call is a clean no-op.
"""

import logging
from importlib.metadata import entry_points

from app.plugins.plugin_context import PluginContext

logger = logging.getLogger("lavs-api")


def load_plugins(context: PluginContext) -> None:
    """Discover every ``lavs.plugins`` entry point and invoke it with ``context``.

    Args:
        context: The extension surface handed to each discovered plugin.
    """
    for entry_point in entry_points(group="lavs.plugins"):
        try:
            plugin = entry_point.load()
            plugin(context)
        except Exception:
            logger.exception("Failed to load LAVS plugin %r; skipping.", entry_point.name)
            continue
        logger.info("Loaded LAVS plugin %r.", entry_point.name)
