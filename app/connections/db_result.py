"""Uniform result handle over a driver's post-execute cursor/relation.

Both DuckDB and psycopg expose the read side of an executed statement through an
object carrying ``fetchone`` / ``fetchall`` / ``description`` / ``rowcount`` — but
they are different concrete types (a ``DuckDBPyConnection`` relation versus a
``psycopg.Cursor``). :class:`DbResult` presents that read side uniformly so query
code is identical across backends.
"""

from collections.abc import Sequence
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class _Fetchable(Protocol):
    """Structural type for the driver object returned by ``execute``."""

    @property
    def description(self) -> Any: ...

    @property
    def rowcount(self) -> int: ...

    def fetchone(self) -> Any: ...

    def fetchall(self) -> Any: ...


class DbResult:
    """A backend-agnostic view over one executed statement's result.

    The wrapped object is the driver handle produced by the underlying
    connection's ``execute`` call (a DuckDB relation or a psycopg cursor). Every
    method delegates to it, giving query code a single, stable shape.
    """

    #: Returned by :attr:`rowcount` when the driver does not report one.
    _UNKNOWN_ROWCOUNT: int = -1

    def __init__(self, cursor: _Fetchable) -> None:
        """Wrap the driver's post-execute handle.

        Args:
            cursor: The object returned by the underlying connection's
                ``execute`` — a DuckDB relation or a psycopg cursor.
        """
        self._cursor = cursor

    def fetchone(self) -> tuple[Any, ...] | None:
        """Return the next result row, or ``None`` when the result is exhausted."""
        return self._cursor.fetchone()

    def fetchall(self) -> list[tuple[Any, ...]]:
        """Return every remaining result row as a list of tuples."""
        return list(self._cursor.fetchall())

    @property
    def description(self) -> Sequence[Any] | None:
        """Return the driver's column description for the executed statement."""
        return self._cursor.description

    @property
    def rowcount(self) -> int:
        """Return the affected/returned row count, or ``-1`` when unknown."""
        rowcount = getattr(self._cursor, "rowcount", self._UNKNOWN_ROWCOUNT)
        return rowcount if isinstance(rowcount, int) else self._UNKNOWN_ROWCOUNT
