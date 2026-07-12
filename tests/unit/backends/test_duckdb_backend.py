"""Unit tests for :class:`DuckDBBackend` connect + schema initialisation."""

import os
import shutil
import tempfile
import uuid
from collections.abc import Iterator

import pytest

import app.configurations.configuration as config_module
from app.backends.backend_kind import BackendKind
from app.backends.duckdb_backend import DuckDBBackend
from app.connections.db_session import DbSession
from app.connections.param_style import ParamStyle

_EXPECTED_TABLES = ["products", "components", "versions", "releases", "release_components"]


@pytest.fixture()
def isolated_db() -> Iterator[str]:
    """Point the configuration at a throwaway DuckDB file for one test."""
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, f"backend_{uuid.uuid4().hex[:8]}.db")

    original_get_database_path = config_module.get_database_path
    original_get_duckdb_database_name = config_module.get_duckdb_database_name
    config_module.get_database_path = lambda: db_path
    config_module.get_duckdb_database_name = lambda: db_path
    config_module.load_database_config.cache_clear()

    try:
        yield db_path
    finally:
        config_module.get_database_path = original_get_database_path
        config_module.get_duckdb_database_name = original_get_duckdb_database_name
        config_module.load_database_config.cache_clear()
        shutil.rmtree(temp_dir, ignore_errors=True)


class TestDuckDBBackendIdentity:
    """The backend reports its kind and placeholder style."""

    def test_name_is_duckdb(self) -> None:
        assert DuckDBBackend().name is BackendKind.DUCKDB

    def test_param_style_is_qmark(self) -> None:
        assert DuckDBBackend().param_style is ParamStyle.QMARK


class TestDuckDBBackendConnect:
    """``connect`` yields a live :class:`DbSession` and closes it on exit."""

    def test_connect_yields_db_session(self, isolated_db: str) -> None:
        # Act
        with DuckDBBackend().connect() as session:
            # Assert
            assert isinstance(session, DbSession)
            assert session.execute("SELECT 1").fetchone() == (1,)


class TestDuckDBBackendInitSchema:
    """``init_schema`` materialises every configured table."""

    def test_init_schema_creates_all_tables(self, isolated_db: str) -> None:
        # Arrange
        backend = DuckDBBackend()

        # Act
        with backend.connect() as session:
            backend.init_schema(session)
            rows = session.execute("SELECT table_name FROM information_schema.tables").fetchall()

        # Assert
        existing = {str(row[0]).lower() for row in rows}
        for table in _EXPECTED_TABLES:
            assert table in existing

    def test_init_schema_is_idempotent(self, isolated_db: str) -> None:
        # Arrange
        backend = DuckDBBackend()

        # Act / Assert: running twice on the same file must not raise.
        with backend.connect() as session:
            backend.init_schema(session)
            backend.init_schema(session)
            row = session.execute("SELECT COUNT(*) FROM products").fetchone()
        assert row == (0,)
