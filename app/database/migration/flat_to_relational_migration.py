"""Idempotent migration from the legacy flat ``Versions`` table to the relational schema."""

import duckdb

from app.database.database_manager import DatabaseManager
from app.database.migration.legacy_schema import LegacySchema
from app.models.enums.component_kind import ComponentKind
from app.models.types.ulid_id import new_ulid

# Defaults for the synthetic component created per migrated product. These are
# constant configuration values (one "default" service component per product),
# named here rather than written as bare literals at the INSERT site.
_DEFAULT_COMPONENT_NAME = "default"
_DEFAULT_COMPONENT_KIND = ComponentKind.SERVICE


class FlatToRelationalMigration:
    """Migrate legacy flat ``Versions`` rows into ``products``/``components``/``versions``.

    The migration is *inspect-then-migrate* and safe to run on every boot:

    * It only acts when a legacy-shaped table (one carrying a ``product_name``
      column) exists with rows **and** the relational ``products`` table is
      empty. Otherwise it is a no-op.
    * One :class:`product` is created per distinct ``product_name``; one
      synthetic ``default`` service :class:`component` per product; and one
      :class:`version` per legacy row, preserving ``major``/``minor``/``patch``
      and the ``status`` 1:1.
    * The legacy rows are preserved (the source table is archived under
      :attr:`LegacySchema.ARCHIVE_TABLE`, not dropped), keeping immutable
      history including duplicate semver rows.

    All data values are written through bound parameters; only schema
    identifiers (table/column names) are interpolated, and those come from the
    :class:`LegacySchema` named constants.
    """

    def run(self, conn: duckdb.DuckDBPyConnection) -> None:
        """Run the migration against a live connection.

        Args:
            conn: The managed DuckDB connection to operate on. No ad-hoc
                connection is opened.
        """
        if not self._should_migrate(conn):
            return

        legacy_rows = self._read_legacy_rows(conn)
        self._archive_source_table(conn)
        # Re-create the relational ``versions`` table now that the colliding
        # legacy name has been archived (``products``/``components`` already
        # exist from schema init; this fills in the freed ``versions`` slot).
        # Run on the same managed connection — DuckDB allows only one writer.
        DatabaseManager.create_tables_on(conn)
        self._insert_relational(conn, legacy_rows)

    def _table_columns(self, conn: duckdb.DuckDBPyConnection, table: str) -> list[str]:
        """Return the lowercase column names of ``table``, or an empty list.

        Args:
            conn: The live connection.
            table: The table to introspect.

        Returns:
            The column names, lowercased; empty when the table is absent.
        """
        try:
            info = conn.execute(f"PRAGMA table_info('{table}')").fetchall()
        except duckdb.Error:
            return []
        return [str(row[1]).lower() for row in info]

    def _row_count(self, conn: duckdb.DuckDBPyConnection, table: str) -> int:
        """Return the number of rows in ``table``, or ``0`` when it is absent.

        Args:
            conn: The live connection.
            table: The table to count.

        Returns:
            The row count, or ``0`` if the table does not exist.
        """
        try:
            result = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
        except duckdb.Error:
            return 0
        return int(result[0]) if result is not None else 0

    def _should_migrate(self, conn: duckdb.DuckDBPyConnection) -> bool:
        """Decide whether a migration is warranted (idempotency gate).

        Migrate only when the source table is present in its *legacy* shape
        (has a ``product_name`` column), holds rows, and the relational
        ``products`` table is still empty.

        Args:
            conn: The live connection.

        Returns:
            True when the migration should run.
        """
        source_columns = self._table_columns(conn, LegacySchema.SOURCE_TABLE)
        is_legacy_shape = LegacySchema.PRODUCT_NAME_COLUMN in source_columns
        if not is_legacy_shape:
            return False
        if self._row_count(conn, LegacySchema.SOURCE_TABLE) == 0:
            return False
        return self._row_count(conn, DatabaseManager.PRODUCTS_TABLE) == 0

    def _read_legacy_rows(
        self, conn: duckdb.DuckDBPyConnection
    ) -> list[tuple[str, int, int, int, str | None]]:
        """Read the legacy rows needed to build the relational records.

        Args:
            conn: The live connection.

        Returns:
            Tuples of ``(product_name, major, minor, patch, status)`` ordered so
            output is deterministic.
        """
        rows = conn.execute(
            "SELECT product_name, major, minor, patch, status "
            f"FROM {LegacySchema.SOURCE_TABLE} "
            "ORDER BY product_name, major, minor, patch"
        ).fetchall()
        return [(str(row[0]), int(row[1]), int(row[2]), int(row[3]), row[4]) for row in rows]

    def _archive_source_table(self, conn: duckdb.DuckDBPyConnection) -> None:
        """Park the legacy table aside, freeing the ``versions`` name.

        DuckDB treats table names case-insensitively, so the legacy ``Versions``
        and the relational ``versions`` share one name. Renaming the legacy
        table preserves its rows while letting the relational schema own the
        canonical name.

        Args:
            conn: The live connection.
        """
        conn.execute(
            f"ALTER TABLE {LegacySchema.SOURCE_TABLE} RENAME TO {LegacySchema.ARCHIVE_TABLE}"
        )

    def _insert_relational(
        self,
        conn: duckdb.DuckDBPyConnection,
        legacy_rows: list[tuple[str, int, int, int, str | None]],
    ) -> None:
        """Populate products/components/versions from the legacy rows.

        One product per distinct ``product_name``, one synthetic ``default``
        service component per product, and one version per legacy row with its
        status preserved 1:1. All values are bound parameters.

        Args:
            conn: The live connection.
            legacy_rows: The tuples returned by :meth:`_read_legacy_rows`.
        """
        component_id_by_product: dict[str, str] = {}

        for product_name, major, minor, patch, status in legacy_rows:
            component_id = component_id_by_product.get(product_name)
            if component_id is None:
                component_id = self._create_product_and_component(conn, product_name)
                component_id_by_product[product_name] = component_id

            conn.execute(
                "INSERT INTO versions "
                "(id, component_id, major, minor, patch, prerelease, status) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (new_ulid(), component_id, major, minor, patch, None, status),
            )

    def _create_product_and_component(
        self, conn: duckdb.DuckDBPyConnection, product_name: str
    ) -> str:
        """Create one product and its synthetic default component.

        Args:
            conn: The live connection.
            product_name: The distinct legacy product name.

        Returns:
            The id of the created component (versions hang off this).
        """
        product_id = new_ulid()
        conn.execute(
            "INSERT INTO products (id, name, description) VALUES (?, ?, ?)",
            (product_id, product_name, None),
        )

        component_id = new_ulid()
        conn.execute(
            "INSERT INTO components (id, product_id, name, kind) VALUES (?, ?, ?, ?)",
            (component_id, product_id, _DEFAULT_COMPONENT_NAME, str(_DEFAULT_COMPONENT_KIND)),
        )
        return component_id
