"""Unit tests for :class:`ParamStyle` placeholder translation."""

from app.connections.param_style import ParamStyle


class TestQmarkIsIdentity:
    """The qmark style leaves canonical statements untouched."""

    def test_qmark_leaves_placeholders_unchanged(self) -> None:
        # Arrange
        sql = "SELECT id FROM products WHERE id = ? AND name = ?"

        # Act
        rendered = ParamStyle.QMARK.render(sql)

        # Assert
        assert rendered == sql

    def test_qmark_leaves_literal_percent_unchanged(self) -> None:
        # Arrange
        sql = "SELECT id FROM t WHERE name LIKE '%foo%' AND id = ?"

        # Act
        rendered = ParamStyle.QMARK.render(sql)

        # Assert
        assert rendered == sql


class TestPyformatTranslation:
    """The pyformat style converts qmark tokens and escapes literal percents."""

    def test_each_placeholder_becomes_percent_s(self) -> None:
        # Arrange
        sql = "INSERT INTO t (a, b, c) VALUES (?, ?, ?)"

        # Act
        rendered = ParamStyle.PYFORMAT.render(sql)

        # Assert
        assert rendered == "INSERT INTO t (a, b, c) VALUES (%s, %s, %s)"

    def test_literal_percent_is_escaped_before_placeholders(self) -> None:
        # Arrange: a LIKE pattern with literal percents alongside a placeholder.
        sql = "SELECT id FROM t WHERE name LIKE '%foo%' AND id = ?"

        # Act
        rendered = ParamStyle.PYFORMAT.render(sql)

        # Assert: every literal % is doubled, the ? becomes %s, and no bare %s
        # was introduced by the escaping step.
        assert rendered == "SELECT id FROM t WHERE name LIKE '%%foo%%' AND id = %s"

    def test_no_placeholders_is_percent_safe(self) -> None:
        # Arrange
        sql = "SELECT 1"

        # Act
        rendered = ParamStyle.PYFORMAT.render(sql)

        # Assert
        assert rendered == "SELECT 1"
