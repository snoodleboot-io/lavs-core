"""Tests for the config-driven DatabaseManager life-cycle."""

import os
import shutil
import tempfile
import uuid
from collections.abc import Iterator

import pytest

import app.configurations.configuration as config_module
from app.backends.backend_factory import BackendFactory
from app.database.database_manager import DatabaseManager

EXPECTED_TABLES = [
    "products",
    "components",
    "versions",
    "releases",
    "release_components",
]


@pytest.fixture()
def isolated_db() -> Iterator[str]:
    """Point the configuration at a throwaway DuckDB file for one test."""
    # Arrange: a unique temp database and patched config accessors.
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, f"test_{uuid.uuid4().hex[:8]}.db")

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


def _existing_tables() -> list[str]:
    """Return the table names currently present in the configured database.

    Uses the portable ``information_schema.tables`` listing (the same one
    :class:`DatabaseManager` now relies on) rather than DuckDB's dialect-specific
    ``SHOW ALL TABLES``.
    """
    with BackendFactory().create().connect() as session:
        rows = session.execute("SELECT table_name FROM information_schema.tables").fetchall()
    return [str(row[0]).lower() for row in rows]


def test_create_tables_creates_all_configured_tables(isolated_db: str) -> None:
    """create_tables must materialise every configured table."""
    # Act
    DatabaseManager.create_tables()

    # Assert
    existing = _existing_tables()
    for table_name in EXPECTED_TABLES:
        assert table_name in existing


def test_create_tables_is_idempotent(isolated_db: str) -> None:
    """Running create_tables twice must not raise."""
    # Act
    DatabaseManager.create_tables()
    DatabaseManager.create_tables()

    # Assert
    existing = _existing_tables()
    for table_name in EXPECTED_TABLES:
        assert table_name in existing


def test_drop_tables_removes_all_configured_tables(isolated_db: str) -> None:
    """drop_tables must remove every configured table."""
    # Arrange
    DatabaseManager.create_tables()

    # Act
    DatabaseManager.drop_tables()

    # Assert
    existing = _existing_tables()
    for table_name in EXPECTED_TABLES:
        assert table_name not in existing


def test_drop_tables_is_safe_when_absent(isolated_db: str) -> None:
    """drop_tables on an empty database must not raise."""
    # Act / Assert
    DatabaseManager.drop_tables()

    assert _existing_tables() == []
