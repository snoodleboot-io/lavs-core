"""Unit tests for :class:`StatementDialect` whole-statement translation."""

from app.connections.statement_dialect import StatementDialect


class TestAnsiIsIdentity:
    """The ANSI dialect leaves canonical ``LIMIT`` statements untouched."""

    def test_ansi_leaves_limit_unchanged(self) -> None:
        # Arrange
        sql = "SELECT id FROM products WHERE name = ? ORDER BY id LIMIT 1"

        # Act
        rendered = StatementDialect.ANSI.render(sql)

        # Assert
        assert rendered == sql


class TestTsqlLimitToTop:
    """The T-SQL dialect rewrites a trailing ``LIMIT n`` into a leading ``TOP n``."""

    def test_trailing_limit_becomes_leading_top(self) -> None:
        # Arrange
        sql = "SELECT id FROM releases WHERE product_id = ? ORDER BY created_at DESC LIMIT 1"

        # Act
        rendered = StatementDialect.TSQL.render(sql)

        # Assert
        assert rendered == (
            "SELECT TOP 1 id FROM releases WHERE product_id = ? ORDER BY created_at DESC"
        )

    def test_top_is_inserted_after_distinct(self) -> None:
        # Arrange
        sql = "SELECT DISTINCT name FROM products LIMIT 5"

        # Act
        rendered = StatementDialect.TSQL.render(sql)

        # Assert
        assert rendered == "SELECT DISTINCT TOP 5 name FROM products"

    def test_larger_row_count_is_preserved(self) -> None:
        # Arrange
        sql = "SELECT id FROM t LIMIT 42"

        # Act
        rendered = StatementDialect.TSQL.render(sql)

        # Assert
        assert rendered == "SELECT TOP 42 id FROM t"

    def test_statement_without_limit_is_unchanged(self) -> None:
        # Arrange
        sql = "SELECT id FROM products WHERE id = ?"

        # Act
        rendered = StatementDialect.TSQL.render(sql)

        # Assert
        assert rendered == sql

    def test_non_select_with_limit_word_is_untouched(self) -> None:
        # Arrange: an UPDATE never carries a top-n clause the rewrite could place.
        sql = "UPDATE versions SET status = ? WHERE id = ?"

        # Act
        rendered = StatementDialect.TSQL.render(sql)

        # Assert
        assert rendered == sql
