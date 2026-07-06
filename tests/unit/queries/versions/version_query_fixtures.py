"""Shared in-memory DuckDB helpers for the version query unit tests.

Each helper builds an isolated ``:memory:`` DuckDB seeded from the real DDL so
the query classes run against the production schema.
"""

import pathlib

import duckdb

from app.models.types.ulid_id import new_ulid

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[4]
_DDL_PATH = _REPO_ROOT / "app" / "database" / "duckdb" / "ddl.sql"


def make_connection() -> duckdb.DuckDBPyConnection:
    """Open an isolated in-memory DuckDB with the real LAVS schema applied.

    Returns:
        A live in-memory connection whose schema matches ``ddl.sql``.
    """
    connection = duckdb.connect(":memory:")
    connection.execute(_DDL_PATH.read_text())
    return connection


def seed_component(connection: duckdb.DuckDBPyConnection) -> str:
    """Insert a product and a component, returning the component id.

    Args:
        connection: The connection to seed.

    Returns:
        The id of the freshly inserted component.
    """
    product_id = new_ulid()
    component_id = new_ulid()
    connection.execute("INSERT INTO products (id, name) VALUES (?, ?)", (product_id, "product"))
    connection.execute(
        "INSERT INTO components (id, product_id, name, kind) VALUES (?, ?, ?, ?)",
        (component_id, product_id, "component", "library"),
    )
    return component_id


def seed_version(
    connection: duckdb.DuckDBPyConnection,
    component_id: str,
    major: int,
    minor: int,
    patch: int,
    status: str,
    prerelease: str | None = None,
) -> str:
    """Insert a version row and return its id.

    Args:
        connection: The connection to seed.
        component_id: The owning component id.
        major: Semver major.
        minor: Semver minor.
        patch: Semver patch.
        status: The lifecycle status to store.
        prerelease: Optional prerelease label.

    Returns:
        The id of the inserted version row.
    """
    version_id = new_ulid()
    connection.execute(
        "INSERT INTO versions "
        "(id, component_id, major, minor, patch, prerelease, status) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (version_id, component_id, major, minor, patch, prerelease, status),
    )
    return version_id
