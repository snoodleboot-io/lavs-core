"""Unit tests for :class:`DbResult` over a real DuckDB relation."""

import duckdb

from app.connections.db_result import DbResult


class TestDbResultOverDuckDB:
    """A DuckDB relation is exposed uniformly through :class:`DbResult`."""

    def _connect(self) -> duckdb.DuckDBPyConnection:
        conn = duckdb.connect(":memory:")
        conn.execute("CREATE TABLE t (id INTEGER, name VARCHAR)")
        conn.execute("INSERT INTO t VALUES (1, 'a'), (2, 'b')")
        return conn

    def test_fetchall_returns_all_rows(self) -> None:
        # Arrange
        conn = self._connect()
        result = DbResult(conn.execute("SELECT id, name FROM t ORDER BY id"))

        # Act
        rows = result.fetchall()

        # Assert
        assert rows == [(1, "a"), (2, "b")]

    def test_fetchone_returns_first_row(self) -> None:
        # Arrange
        conn = self._connect()
        result = DbResult(conn.execute("SELECT id FROM t ORDER BY id"))

        # Act
        row = result.fetchone()

        # Assert
        assert row == (1,)

    def test_description_exposes_column_names(self) -> None:
        # Arrange
        conn = self._connect()
        result = DbResult(conn.execute("SELECT id, name FROM t"))

        # Act
        description = result.description

        # Assert
        assert description is not None
        assert [column[0] for column in description] == ["id", "name"]

    def test_rowcount_is_an_int(self) -> None:
        # Arrange
        conn = self._connect()
        result = DbResult(conn.execute("SELECT id FROM t"))

        # Act / Assert: DuckDB does not always report a rowcount, so the wrapper
        # guarantees an int (``-1`` when unknown) rather than raising.
        assert isinstance(result.rowcount, int)
