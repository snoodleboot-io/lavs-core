"""Adapt a PyMySQL connection to the ``execute``-returns-fetchable contract.

:class:`~app.connections.db_session.DbSession` drives every backend through a
single call shape — ``connection.execute(sql, params)`` returning a fetchable
handle carrying ``fetchone`` / ``fetchall`` / ``description`` / ``rowcount``.
DuckDB and psycopg connections offer that method natively; PyMySQL does not — it
exposes execution only through a cursor obtained from ``connection.cursor()``.

:class:`PyMySqlConnection` bridges that gap: it wraps a live PyMySQL connection
and presents the same ``execute`` method, opening a fresh (buffered) cursor per
statement and returning it as the fetchable handle. The wrapper is otherwise
transparent — autocommit configuration and closing stay the caller's concern,
handled by :class:`~app.backends.mysql_backend.MySqlBackend` on the raw
connection it owns.
"""

from collections.abc import Sequence
from typing import Any


class PyMySqlConnection:
    """A PyMySQL connection presenting DuckDB/psycopg-style ``execute``."""

    def __init__(self, connection: Any) -> None:
        """Wrap a live PyMySQL connection.

        Args:
            connection: The raw ``pymysql.connections.Connection`` whose
                cursors are used to run statements.
        """
        self._connection = connection

    def execute(self, sql: str, params: Sequence[Any] | None = None) -> Any:
        """Execute one statement and return its cursor as a fetchable handle.

        A fresh cursor is opened for each statement (PyMySQL's default cursor is
        buffered, so its result set stays valid after later cursors are opened),
        mirroring how psycopg's ``Connection.execute`` yields a new cursor per
        call. The bound ``params`` are handed to the driver untouched.

        Args:
            sql: The statement to run, already rendered into PyMySQL's pyformat
                (``%s``) placeholder style by :class:`DbSession`.
            params: The bound parameter values, or ``None`` for a parameterless
                statement.

        Returns:
            The executed PyMySQL cursor, ready to be read via ``fetchone`` /
            ``fetchall`` / ``description`` / ``rowcount``.
        """
        cursor = self._connection.cursor()
        if params is None:
            cursor.execute(sql)
        else:
            cursor.execute(sql, params)
        return cursor
