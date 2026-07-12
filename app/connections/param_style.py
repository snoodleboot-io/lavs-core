"""Parameter placeholder styles understood by :class:`DbSession`.

Query code across the codebase is written with a single, uniform placeholder
token — the qmark ``?`` — regardless of the backend it ultimately runs on. The
:class:`DbSession` wrapper rewrites that token into the concrete driver's
placeholder style at execution time. Each member owns the rewrite for its style
so the wrapper never branches on bare string literals.
"""

from enum import StrEnum
from typing import Final

#: The canonical placeholder token every statement across the codebase is
#: authored with. Rewrites target this token; it is never a bare literal at a
#: call site.
CANONICAL_PLACEHOLDER: Final[str] = "?"

#: The pyformat placeholder token and the escaped form of a literal percent.
_PYFORMAT_PLACEHOLDER: Final[str] = "%s"
_PERCENT: Final[str] = "%"
_ESCAPED_PERCENT: Final[str] = "%%"


class ParamStyle(StrEnum):
    """A driver placeholder style plus the rewrite from the canonical qmark form.

    The canonical form authored throughout the codebase uses ``?`` placeholders.
    :meth:`render` translates a canonical statement into the concrete style. The
    translation is *value-safe*: it only rewrites the ``?`` tokens and escapes
    literal ``%`` where the target style is percent-based — bound values are
    passed to the driver separately and are never touched.
    """

    #: DuckDB (and the sqlite family): native ``?`` placeholders. Identity.
    QMARK = "qmark"
    #: psycopg / DB-API pyformat: ``%s`` placeholders, literal ``%`` doubled.
    PYFORMAT = "pyformat"

    def render(self, sql: str) -> str:
        """Rewrite a canonical (``?``-placeholder) statement into this style.

        Args:
            sql: A SQL statement using ``?`` placeholders and, at most, literal
                ``%`` characters (never a literal ``?`` inside a string literal —
                the codebase carries none).

        Returns:
            The statement rewritten for this placeholder style. ``QMARK`` returns
            it unchanged; ``PYFORMAT`` escapes every literal ``%`` to ``%%`` and
            then converts each ``?`` to ``%s``.
        """
        if self is ParamStyle.QMARK:
            return sql
        escaped = sql.replace(_PERCENT, _ESCAPED_PERCENT)
        return escaped.replace(CANONICAL_PLACEHOLDER, _PYFORMAT_PLACEHOLDER)
