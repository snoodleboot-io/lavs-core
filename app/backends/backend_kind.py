"""The set of persistence backends the application can be configured to use."""

from enum import StrEnum


class BackendKind(StrEnum):
    """Identifier for a concrete persistence backend.

    The string values double as the accepted ``LAVS_DB_BACKEND`` configuration
    tokens, so configuration parsing never carries a bare backend-name literal.
    """

    #: File-based, single-writer, zero-setup — the local/test default.
    DUCKDB = "duckdb"
    #: Networked, concurrent — the production target (implemented by the R1 lane).
    POSTGRES = "postgres"
    #: Networked, concurrent — the MySQL/InnoDB target (PyMySQL driver).
    MYSQL = "mysql"
    #: Networked, concurrent — the SQL Server target (pymssql driver).
    MSSQL = "mssql"
