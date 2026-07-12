"""Uniform, dialect-agnostic session wrapper over a raw driver connection.

Query code throughout the codebase calls ``session.execute(sql, params)`` with
``?`` placeholders and then reads the result via ``fetchone`` / ``fetchall`` /
``description``. :class:`DbSession` makes that shape work over any backend: it
rewrites the ``?`` placeholders into the backend's placeholder style (see
:class:`~app.connections.param_style.ParamStyle`) and wraps the driver's
post-execute handle in a :class:`~app.connections.db_result.DbResult`.

The wrapper is strictly value-safe: it rewrites only the placeholder *tokens* of
the statement text and never interpolates a bound value. Values continue to
travel to the driver through its own parameter binding.
"""

from collections.abc import Sequence
from typing import Any

from app.connections.db_result import DbResult
from app.connections.param_style import ParamStyle


class DbSession:
    """A backend-agnostic session over a raw driver connection."""

    def __init__(self, connection: Any, param_style: ParamStyle) -> None:
        """Wrap a live driver connection with its placeholder style.

        Args:
            connection: The raw driver connection (a ``DuckDBPyConnection`` or a
                ``psycopg.Connection``) whose ``execute`` returns a fetchable
                handle.
            param_style: The placeholder style the underlying driver expects.
        """
        self._connection = connection
        self._param_style = param_style

    @property
    def param_style(self) -> ParamStyle:
        """Return the placeholder style this session translates into."""
        return self._param_style

    @property
    def raw_connection(self) -> Any:
        """Return the underlying driver connection.

        Provided only as an escape hatch for the rare operation that cannot be
        expressed through :meth:`execute`; query code should not reach for it.
        """
        return self._connection

    def execute(self, sql: str, params: Sequence[Any] | None = None) -> DbResult:
        """Execute a canonical (``?``-placeholder) statement and return its result.

        The statement's placeholders are rewritten into the backend's style
        before execution; the bound ``params`` are handed to the driver
        untouched, so no value is ever interpolated into the statement text.

        Args:
            sql: A SQL statement using ``?`` placeholders.
            params: The bound parameter values, or ``None`` for a parameterless
                statement.

        Returns:
            A :class:`DbResult` over the executed statement.
        """
        rendered = self._param_style.render(sql)
        if params is None:
            cursor = self._connection.execute(rendered)
        else:
            cursor = self._connection.execute(rendered, params)
        return DbResult(cursor)
