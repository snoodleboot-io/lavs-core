"""Acceptance: zero string-interpolated SQL (P0 'Fix SQL injection').

ROADMAP P0 acceptance: "no string-interpolated SQL anywhere". Guiding principle:
"Parameterized SQL only -- no string-interpolated queries, ever."

This static guard scans every module under ``app/queries`` and fails if any SQL-looking
string is built via an f-string (``ast.JoinedStr`` with interpolated fields) or via
``str.format``. The known offender is
``app/queries/patch_version/create_patch.py`` (f-string ``INSERT``); it is expected to
be RED until the P0 SQL-parameterization lane lands.

The scan is intentionally narrow: it only flags interpolated string LITERALS whose
text contains a SQL keyword, and ``.format(...)`` calls on string literals containing a
SQL keyword. Plain parameterized queries (``conn.sql("... ?", params=(...))``) pass.
"""

import ast
import pathlib

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_QUERIES_DIR = _REPO_ROOT / "app" / "queries"

# SQL statement verbs that begin a DML/DDL query. A string is treated as SQL only when
# its leading (stripped) text starts with one of these -- this distinguishes genuine
# query construction (e.g. "INSERT INTO ...") from prose that merely contains a keyword
# (e.g. an error message: "... Create a base version first ...").
_SQL_STATEMENT_VERBS = (
    "select ",
    "insert into",
    "insert ",
    "update ",
    "delete from",
    "delete ",
    "create table",
    "create sequence",
    "drop ",
    "alter ",
    "with ",
)


def _looks_like_sql(text: str) -> bool:
    """Return True if a string fragment is a SQL statement.

    The heuristic requires the leading (whitespace-stripped) text to begin with a SQL
    statement verb. This avoids false positives on prose strings that merely embed a
    SQL keyword somewhere in the middle.

    Args:
        text: The literal text to inspect.

    Returns:
        True when the text begins with a recognized SQL statement verb.
    """
    lowered = text.lstrip().lower()
    return any(lowered.startswith(verb) for verb in _SQL_STATEMENT_VERBS)


def _static_text_of_joinedstr(node: ast.JoinedStr) -> str:
    """Concatenate the constant (non-interpolated) text parts of an f-string.

    Args:
        node: The ``ast.JoinedStr`` node.

    Returns:
        The constant text fragments joined together.
    """
    parts: list[str] = []
    for value in node.values:
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            parts.append(value.value)
    return "".join(parts)


def _has_interpolation(node: ast.JoinedStr) -> bool:
    """Return True if the f-string contains at least one interpolated expression.

    Args:
        node: The ``ast.JoinedStr`` node.

    Returns:
        True when a ``FormattedValue`` is present.
    """
    return any(isinstance(value, ast.FormattedValue) for value in node.values)


def _query_modules() -> list[pathlib.Path]:
    """Collect all Python modules under ``app/queries``.

    Returns:
        Sorted list of module paths (excluding ``__pycache__``).
    """
    return sorted(path for path in _QUERIES_DIR.rglob("*.py") if "__pycache__" not in path.parts)


def _find_string_sql_offenses(path: pathlib.Path) -> list[str]:
    """Find f-string / ``.format`` SQL construction in a single module.

    Args:
        path: The module to scan.

    Returns:
        A list of human-readable offense descriptions (empty if clean).
    """
    source = path.read_text()
    tree = ast.parse(source, filename=str(path))
    rel = path.relative_to(_REPO_ROOT)
    offenses: list[str] = []

    for node in ast.walk(tree):
        # f-string SQL: an interpolated JoinedStr whose static text looks like SQL.
        if isinstance(node, ast.JoinedStr) and _has_interpolation(node):
            text = _static_text_of_joinedstr(node)
            if _looks_like_sql(text):
                offenses.append(
                    f"{rel}:{node.lineno}: f-string interpolated SQL "
                    f"(use parameterized queries with '?' placeholders)"
                )
        # str.format SQL: "...".format(...) on a literal that looks like SQL.
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "format"
            and isinstance(node.func.value, ast.Constant)
            and isinstance(node.func.value.value, str)
            and _looks_like_sql(node.func.value.value)
        ):
            offenses.append(
                f"{rel}:{node.lineno}: str.format() interpolated SQL "
                f"(use parameterized queries with '?' placeholders)"
            )

    return offenses


class TestNoStringInterpolatedSql:
    """P0 exit criterion: no string-interpolated SQL under app/queries."""

    def test_queries_directory_exists(self) -> None:
        """Guard: the scanned directory must exist (fail loudly if relocated)."""
        assert _QUERIES_DIR.is_dir(), f"expected query package at {_QUERIES_DIR}"

    def test_no_fstring_or_format_sql_in_queries(self) -> None:
        """No module under app/queries may build SQL via f-string or .format()."""
        all_offenses: list[str] = []
        for module in _query_modules():
            all_offenses.extend(_find_string_sql_offenses(module))

        assert not all_offenses, "String-interpolated SQL detected (P0 forbids it):\n" + "\n".join(
            all_offenses
        )
