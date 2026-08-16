"""Statement-shape dialects understood by :class:`DbSession`.

Query code across the codebase is authored once, in a single portable SQL shape,
and run unchanged on every backend. Placeholder *tokens* are handled separately
by :class:`~app.connections.param_style.ParamStyle`; this module handles the few
whole-statement constructs whose *syntax* genuinely diverges between engines.

DuckDB, PostgreSQL, and MySQL all speak the ``LIMIT n`` row-limiting clause the
query layer is written with, so their dialect is the identity transform. SQL
Server has no ``LIMIT`` — a top-n query is spelled ``SELECT TOP n`` — so its
dialect rewrites a trailing ``LIMIT n`` into a leading ``TOP n``. The rewrite is
value-safe: it moves only the literal row count (always an integer literal in the
codebase, never a bound parameter) and never touches a placeholder or a value.
"""

import re
from enum import StrEnum
from typing import Final

#: A trailing ``LIMIT <n>`` clause (integer literal only — the codebase never
#: binds the row count as a parameter), anchored to the end of the statement.
_TRAILING_LIMIT: Final[re.Pattern[str]] = re.compile(r"\s+LIMIT\s+(\d+)\s*\Z", re.IGNORECASE)
#: The leading ``SELECT`` (with an optional ``DISTINCT``) a ``TOP`` clause is
#: inserted after.
_SELECT_HEAD: Final[re.Pattern[str]] = re.compile(r"\ASELECT\s+(?:DISTINCT\s+)?", re.IGNORECASE)


class StatementDialect(StrEnum):
    """A whole-statement SQL shape plus the rewrite from the canonical form.

    The canonical form authored throughout the codebase uses the ``LIMIT n``
    row-limiting clause. :meth:`render` translates a canonical statement into the
    concrete engine's shape. The translation is *value-safe*: it only relocates
    the integer row count and never rewrites a placeholder or a bound value.
    """

    #: DuckDB / PostgreSQL / MySQL: native ``LIMIT n``. Identity.
    ANSI = "ansi"
    #: SQL Server: a trailing ``LIMIT n`` becomes a leading ``SELECT TOP n``.
    TSQL = "tsql"

    def render(self, sql: str) -> str:
        """Rewrite a canonical statement into this engine's shape.

        Args:
            sql: A SQL statement using the canonical ``LIMIT n`` clause for row
                limiting.

        Returns:
            The statement rewritten for this dialect. ``ANSI`` returns it
            unchanged; ``TSQL`` moves a trailing ``LIMIT n`` into a ``TOP n``
            immediately after the leading ``SELECT`` (a statement with no
            trailing ``LIMIT``, or one this rewrite cannot place, is returned
            unchanged).
        """
        if self is StatementDialect.ANSI:
            return sql
        limit = _TRAILING_LIMIT.search(sql)
        if limit is None:
            return sql
        head = _SELECT_HEAD.match(sql)
        if head is None:
            return sql
        body = sql[: limit.start()]
        return f"{body[: head.end()]}TOP {limit.group(1)} {body[head.end() :]}"
