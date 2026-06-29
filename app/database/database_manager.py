"""Config-driven life-cycle management for the database schema."""

import os

from app.configurations.configuration import load_database_config
from app.connections.connection_factory import ConnectionFactory


class DatabaseManager:
    """Manage the life-cycle of the database.

    Initialisation is config-driven: the set of tables is read from
    ``database.yaml`` (via :func:`load_database_config`) while the concrete DDL
    lives in ``duckdb/ddl.sql``. No table name is hardcoded here.
    """

    @classmethod
    def _table_names(cls) -> list[str]:
        """Return the configured table names from ``database.yaml``."""
        config = load_database_config()
        return [table.name for table in config.database.tables]

    @classmethod
    def _existing_tables(cls, conn) -> list[str]:
        """Return the names of the tables currently present in the database.

        ``SHOW ALL TABLES`` yields rows of the form
        ``(database, schema, name, ...)`` so the table name is at index 2.
        """
        table_result = conn.execute("SHOW ALL TABLES").fetchall()
        return [row[2] for row in table_result]

    @classmethod
    def create_tables(cls) -> None:
        """Create the configured tables by running ``ddl.sql``.

        After running the DDL, every table named in the configuration is
        verified to exist.

        Raises:
            AssertionError: When a configured table is missing after init.
        """
        ddl_path = os.path.join(os.path.dirname(__file__), "duckdb/ddl.sql")
        with ConnectionFactory().retrieve(key="duckdb") as conn:
            with open(ddl_path, encoding="utf-8") as stream:
                query = stream.read()
            conn.execute(query=query)

            existing = cls._existing_tables(conn)
            for table_name in cls._table_names():
                assert table_name in existing, f"Expected table '{table_name}' to exist after init."

    @classmethod
    def drop_tables(cls) -> None:
        """Drop each configured table if it is present.

        Tables are dropped in the reverse of their configured order so that
        child tables are removed before the parents they reference, satisfying
        DuckDB's foreign-key constraints.
        """
        with ConnectionFactory().retrieve(key="duckdb") as conn:
            existing = cls._existing_tables(conn)
            for table_name in reversed(cls._table_names()):
                if table_name in existing:
                    conn.execute(query=f"DROP TABLE {table_name}")
