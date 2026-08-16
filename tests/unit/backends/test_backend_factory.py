"""Unit tests for :class:`BackendFactory` selection and the R1 registration seam."""

from collections.abc import Iterator

import pytest

from app.backends.backend_factory import BackendFactory
from app.backends.backend_kind import BackendKind
from app.backends.backend_settings import BackendSettings
from app.backends.duckdb_backend import DuckDBBackend
from app.backends.unsupported_backend_error import UnsupportedBackendError


@pytest.fixture()
def preserved_registry() -> Iterator[None]:
    """Snapshot and restore the class-level builder registry around a test."""
    original = dict(BackendFactory._registry)
    try:
        yield
    finally:
        BackendFactory._registry = original


class TestBackendFactorySelection:
    """The factory builds the backend named by the settings."""

    def test_default_builds_duckdb_backend(self) -> None:
        # Arrange
        settings = BackendSettings(backend=BackendKind.DUCKDB)

        # Act
        backend = BackendFactory(settings).create()

        # Assert
        assert isinstance(backend, DuckDBBackend)

    def test_postgres_is_registered(self) -> None:
        # Arrange: the Postgres lane self-registers on import of app.backends.
        from app.backends.postgres_backend import PostgresBackend

        settings = BackendSettings(backend=BackendKind.POSTGRES)

        # Act
        backend = BackendFactory(settings).create()

        # Assert
        assert isinstance(backend, PostgresBackend)

    def test_mysql_is_registered(self) -> None:
        # Arrange: the MySQL lane self-registers on import of app.backends.
        from app.backends.mysql_backend import MySqlBackend

        settings = BackendSettings(backend=BackendKind.MYSQL)

        # Act
        backend = BackendFactory(settings).create()

        # Assert
        assert isinstance(backend, MySqlBackend)

    def test_unregistered_backend_raises(self, preserved_registry: None) -> None:
        # Arrange: drop the Postgres builder so its kind has no registered builder.
        BackendFactory._registry.pop(BackendKind.POSTGRES, None)
        settings = BackendSettings(backend=BackendKind.POSTGRES)

        # Act / Assert
        with pytest.raises(UnsupportedBackendError) as excinfo:
            BackendFactory(settings).create()
        assert excinfo.value.kind is BackendKind.POSTGRES


class TestBackendFactoryRegistrationSeam:
    """A new backend comes online purely by registering a builder (the R1 seam)."""

    def test_registered_builder_is_used(self, preserved_registry: None) -> None:
        # Arrange
        sentinel = DuckDBBackend()
        BackendFactory.register(BackendKind.POSTGRES, lambda settings: sentinel)
        settings = BackendSettings(backend=BackendKind.POSTGRES)

        # Act
        backend = BackendFactory(settings).create()

        # Assert
        assert backend is sentinel
