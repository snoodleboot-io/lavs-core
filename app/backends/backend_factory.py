"""Config-driven construction of the active :class:`Backend`.

The factory maps each :class:`BackendKind` to a builder and selects one from
:class:`BackendSettings` (``LAVS_DB_BACKEND``, default DuckDB). DuckDB is
registered here; a separate lane registers its backend by calling
:meth:`BackendFactory.register` at import time — for example R1::

    from app.backends.backend_factory import BackendFactory
    from app.backends.backend_kind import BackendKind
    BackendFactory.register(
        BackendKind.POSTGRES, lambda settings: PostgresBackend(settings)
    )

That is the entire seam: no change to this module, the query layer, or the
lifespan is needed to bring a new backend online.
"""

from collections.abc import Callable

from app.backends.backend import Backend
from app.backends.backend_kind import BackendKind
from app.backends.backend_settings import BackendSettings
from app.backends.duckdb_backend import DuckDBBackend
from app.backends.unsupported_backend_error import UnsupportedBackendError

#: A builder turns the resolved settings into a live backend instance.
BackendBuilder = Callable[[BackendSettings], Backend]


class BackendFactory:
    """Build the configured :class:`Backend` from :class:`BackendSettings`."""

    _registry: dict[BackendKind, BackendBuilder] = {
        BackendKind.DUCKDB: lambda settings: DuckDBBackend(),
    }

    def __init__(self, settings: BackendSettings | None = None) -> None:
        """Initialise the factory.

        Args:
            settings: The backend settings to select from. Defaults to settings
                read from the environment.
        """
        self._settings = settings or BackendSettings()

    @classmethod
    def register(cls, kind: BackendKind, builder: BackendBuilder) -> None:
        """Register (or replace) the builder for a backend kind.

        Args:
            kind: The backend the builder constructs.
            builder: A callable turning :class:`BackendSettings` into a
                :class:`Backend`.
        """
        cls._registry[kind] = builder

    def create(self) -> Backend:
        """Build the backend selected by the settings.

        Returns:
            A live :class:`Backend` for the configured kind.

        Raises:
            UnsupportedBackendError: When the selected kind has no builder
                registered (its lane is not installed).
        """
        kind = self._settings.backend()
        builder = self._registry.get(kind)
        if builder is None:
            raise UnsupportedBackendError(kind, list(self._registry.keys()))
        return builder(self._settings)
