"""Split a DDL script into individually executable statements.

PostgreSQL, over the extended-query protocol psycopg uses, rejects a multi-
statement ``execute``. The LAVS DDL scripts are plain schema statements with no
semicolons inside string literals and only line (``--``) comments, so splitting
on the semicolon terminator after stripping comment lines yields the individual
statements safely. This is factored out of :class:`~app.backends.postgres_backend.PostgresBackend`
so the split rule lives in one tested place rather than inline at the call site.
"""

from typing import Final

#: The statement terminator every DDL statement ends with.
_STATEMENT_TERMINATOR: Final[str] = ";"
#: The prefix marking a whole-line SQL comment in the DDL scripts.
_LINE_COMMENT_PREFIX: Final[str] = "--"


class DdlScript:
    """A DDL script that can enumerate its individual statements."""

    def __init__(self, text: str) -> None:
        """Wrap the raw DDL text.

        Args:
            text: The full DDL script, possibly holding several ``;``-terminated
                statements and ``--`` line comments.
        """
        self._text = text

    def statements(self) -> list[str]:
        """Return the script's statements, comments and blank lines removed.

        Whole-line ``--`` comments are dropped first (the DDL carries no inline
        comments and no semicolons inside literals), then the remaining text is
        split on the statement terminator and each non-empty statement is
        stripped of surrounding whitespace.

        Returns:
            The ordered, non-empty statements ready to execute one at a time.
        """
        code_lines = [
            line
            for line in self._text.splitlines()
            if not line.strip().startswith(_LINE_COMMENT_PREFIX)
        ]
        joined = "\n".join(code_lines)
        return [
            statement.strip()
            for statement in joined.split(_STATEMENT_TERMINATOR)
            if statement.strip()
        ]
