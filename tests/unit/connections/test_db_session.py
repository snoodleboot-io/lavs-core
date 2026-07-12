"""Unit tests for :class:`DbSession` over a real DuckDB connection."""

import duckdb

from app.connections.db_result import DbResult
from app.connections.db_session import DbSession
from app.connections.param_style import ParamStyle


def _duckdb_session() -> DbSession:
    conn = duckdb.connect(":memory:")
    session = DbSession(conn, ParamStyle.QMARK)
    session.execute("CREATE TABLE t (id INTEGER, name VARCHAR)")
    return session


class TestDbSessionExecute:
    """Execution binds values safely and returns a uniform result."""

    def test_execute_returns_db_result(self) -> None:
        # Arrange
        session = _duckdb_session()

        # Act
        result = session.execute("SELECT 1")

        # Assert
        assert isinstance(result, DbResult)

    def test_parameterized_round_trip(self) -> None:
        # Arrange
        session = _duckdb_session()

        # Act
        session.execute("INSERT INTO t (id, name) VALUES (?, ?)", [7, "seven"])
        row = session.execute("SELECT id, name FROM t WHERE id = ?", [7]).fetchone()

        # Assert
        assert row == (7, "seven")

    def test_values_with_placeholder_characters_are_not_interpolated(self) -> None:
        # Arrange: a value containing both '?' and '%' must survive untouched,
        # proving the wrapper rewrites only statement tokens, never values.
        session = _duckdb_session()
        tricky = "50% off? yes"

        # Act
        session.execute("INSERT INTO t (id, name) VALUES (?, ?)", [1, tricky])
        row = session.execute("SELECT name FROM t WHERE id = ?", [1]).fetchone()

        # Assert
        assert row is not None
        assert row[0] == tricky


class TestDbSessionAccessors:
    """The session exposes its style and, as an escape hatch, its raw handle."""

    def test_param_style_is_reported(self) -> None:
        # Arrange
        session = _duckdb_session()

        # Act / Assert
        assert session.param_style is ParamStyle.QMARK

    def test_raw_connection_is_the_underlying_driver(self) -> None:
        # Arrange
        conn = duckdb.connect(":memory:")
        session = DbSession(conn, ParamStyle.QMARK)

        # Act / Assert
        assert session.raw_connection is conn
