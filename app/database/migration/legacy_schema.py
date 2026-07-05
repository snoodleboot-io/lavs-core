"""Named identifiers for the legacy flat schema (no magic strings)."""

from enum import StrEnum


class LegacySchema(StrEnum):
    """SQL identifiers involved in the flat-to-relational migration.

    These are schema identifiers (table/column names), not data values, so they
    are interpolated into DDL as named constants rather than passed as bound
    parameters. They are gathered here so the migration carries no bare string
    literals for table or column names.
    """

    # The single flat table the legacy LAVS API wrote releases into.
    SOURCE_TABLE = "versions"
    # The column that uniquely marks a row as belonging to the legacy schema.
    PRODUCT_NAME_COLUMN = "product_name"
    # Where the legacy table is parked once its data has been migrated, so the
    # relational ``versions`` name is free for the new schema while the original
    # rows are preserved.
    ARCHIVE_TABLE = "legacy_versions"
