"""Tests for the idempotent flat-to-relational startup migration."""

import os
import shutil
import tempfile
import uuid
from collections.abc import Iterator

import pytest

import app.configurations.configuration as config_module
from app.connections.connection_factory import ConnectionFactory
from app.database.database_manager import DatabaseManager
from app.database.migration.flat_to_relational_migration import (
    FlatToRelationalMigration,
)

_LEGACY_DDL = (
    "CREATE TABLE Versions ("
    "id INTEGER, major INTEGER, minor INTEGER, patch INTEGER, "
    "product_name VARCHAR, status VARCHAR)"
)


@pytest.fixture()
def isolated_db() -> Iterator[str]:
    """Point the configuration at a throwaway DuckDB file for one test."""
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, f"migration_{uuid.uuid4().hex[:8]}.db")

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


def _seed_legacy_versions(rows: list[tuple[int, int, int, int, str, str]]) -> None:
    """Create a legacy ``Versions`` table and insert the given rows.

    Args:
        rows: Tuples of ``(id, major, minor, patch, product_name, status)``.
    """
    with ConnectionFactory().retrieve(key="duckdb") as conn:
        conn.execute(_LEGACY_DDL)
        for row in rows:
            conn.execute(
                "INSERT INTO Versions "
                "(id, major, minor, patch, product_name, status) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                row,
            )


def _run_migration() -> None:
    """Init the relational schema and run the migration on one connection."""
    with ConnectionFactory().retrieve(key="duckdb") as conn:
        DatabaseManager.create_tables_on(conn)
        FlatToRelationalMigration().run(conn)


def _counts_and_statuses() -> tuple[int, int, int, list[str]]:
    """Return product/component/version counts and the version statuses."""
    with ConnectionFactory().retrieve(key="duckdb") as conn:
        products = int(conn.execute("SELECT COUNT(*) FROM products").fetchone()[0])
        components = int(conn.execute("SELECT COUNT(*) FROM components").fetchone()[0])
        versions = int(conn.execute("SELECT COUNT(*) FROM versions").fetchone()[0])
        statuses = [
            str(row[0])
            for row in conn.execute("SELECT status FROM versions ORDER BY status").fetchall()
        ]
    return products, components, versions, statuses


class TestMigrationPopulatesRelationalSchema:
    """A legacy table with rows is migrated into the relational tables."""

    def test_migration_populates_products_components_versions(self, isolated_db: str) -> None:
        """Two products' rows become products, components and versions."""
        # Arrange
        _seed_legacy_versions(
            [
                (1, 1, 0, 0, "alpha", "active"),
                (2, 1, 1, 0, "alpha", "superseded"),
                (3, 2, 0, 0, "beta", "active"),
            ]
        )

        # Act
        _run_migration()

        # Assert
        products, components, versions, statuses = _counts_and_statuses()
        assert products == 2
        assert components == 2
        assert versions == 3
        assert statuses == ["active", "active", "superseded"]

    def test_migration_preserves_status_per_product(self, isolated_db: str) -> None:
        """Each legacy status is carried onto its migrated version 1:1."""
        # Arrange
        _seed_legacy_versions(
            [
                (1, 1, 0, 0, "alpha", "rolled_back"),
                (2, 1, 1, 0, "alpha", "active"),
            ]
        )

        # Act
        _run_migration()

        # Assert
        with ConnectionFactory().retrieve(key="duckdb") as conn:
            rows = conn.execute(
                "SELECT major, minor, patch, status FROM versions ORDER BY major, minor, patch"
            ).fetchall()
        assert [tuple(row) for row in rows] == [
            (1, 0, 0, "rolled_back"),
            (1, 1, 0, "active"),
        ]

    def test_migration_keeps_duplicate_semver_rows(self, isolated_db: str) -> None:
        """Duplicate semver rows are preserved (immutable history)."""
        # Arrange
        _seed_legacy_versions(
            [
                (1, 1, 0, 0, "alpha", "superseded"),
                (2, 1, 0, 0, "alpha", "active"),
            ]
        )

        # Act
        _run_migration()

        # Assert
        _products, _components, versions, _statuses = _counts_and_statuses()
        assert versions == 2


class TestMigrationIdempotency:
    """The migration is safe to run repeatedly."""

    def test_second_run_is_a_no_op(self, isolated_db: str) -> None:
        """Running migration twice does not duplicate rows."""
        # Arrange
        _seed_legacy_versions([(1, 1, 0, 0, "alpha", "active")])
        _run_migration()

        # Act: run again on a fresh connection.
        with ConnectionFactory().retrieve(key="duckdb") as conn:
            FlatToRelationalMigration().run(conn)

        # Assert
        products, components, versions, _statuses = _counts_and_statuses()
        assert (products, components, versions) == (1, 1, 1)


class TestMigrationNoOpWithoutLegacyTable:
    """With no legacy table present the migration leaves the schema empty."""

    def test_no_op_when_no_legacy_versions_table(self, isolated_db: str) -> None:
        """A fresh relational schema with no legacy data is untouched."""
        # Arrange: only the relational schema, no legacy ``Versions`` rows.
        with ConnectionFactory().retrieve(key="duckdb") as conn:
            DatabaseManager.create_tables_on(conn)

            # Act
            FlatToRelationalMigration().run(conn)

        # Assert
        products, components, versions, _statuses = _counts_and_statuses()
        assert (products, components, versions) == (0, 0, 0)
