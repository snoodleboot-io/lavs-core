from unittest import IsolatedAsyncioTestCase
from unittest.mock import MagicMock

from app.models.requests.application_and_version_model import (
    ApplicationAndVersionNameModel,
)
from app.models.responses.application_and_version_response_model import (
    ApplicationAndVersionResponseModel,
)
from app.queries.patch_version.rollback_to_previous_patch_version import (
    RollbackToPreviousPatchVersion,
)


def _make_result(description: list[tuple], rows: list[tuple]) -> MagicMock:
    """Build a mock query-result object mimicking the DuckDB relation API.

    Args:
        description: Column descriptions (each a tuple whose first element is
            the column name).
        rows: Result rows to return from ``fetchall``.

    Returns:
        A configured ``MagicMock`` exposing ``description`` and ``fetchall``.
    """
    result = MagicMock()
    result.description = description
    result.fetchall.return_value = rows
    return result


class TestRollbackToPreviousPatchVersion(IsolatedAsyncioTestCase):
    """Unit tests for non-destructive rollback behavior."""

    def _build_connection(self) -> MagicMock:
        """Create a mock connection wired for a two-version rollback scenario.

        The connection responds to the active-version lookup, the
        previous-version lookup, and the two UPDATE statements. ``DELETE`` is
        intentionally never wired so that any deletion would surface as a bug.

        Returns:
            A configured ``MagicMock`` connection.
        """
        description = [
            ("major",),
            ("minor",),
            ("patch",),
            ("product_name",),
            ("id",),
            ("status",),
        ]
        active_row = (1, 2, 3, "test", 2, "active")
        previous_row = (1, 2, 2, "test", 1, "superseded")

        conn = MagicMock()

        def _sql(query: str, params: tuple | None = None, **_: object) -> MagicMock:
            normalized = query.strip().upper()
            if normalized.startswith("SELECT"):
                if "STATUS = ?" in query.upper() and params is not None and params[-1] == "active":
                    return _make_result(description, [active_row])
                return _make_result(description, [previous_row])
            return _make_result([], [])

        conn.sql.side_effect = _sql
        return conn

    async def test_rollback_is_non_destructive(self) -> None:
        """Rollback must never issue a DELETE statement."""
        conn = self._build_connection()
        data = ApplicationAndVersionNameModel(product_name="test")

        await RollbackToPreviousPatchVersion().apply(data=data, conn=conn)

        executed_sql = " ".join(
            str(call.args[0]) if call.args else str(call.kwargs.get("query", ""))
            for call in conn.sql.call_args_list
        )
        self.assertNotIn("DELETE", executed_sql.upper())

    async def test_rollback_marks_current_row_rolled_back(self) -> None:
        """The current active row is updated to status 'rolled_back'."""
        conn = self._build_connection()
        data = ApplicationAndVersionNameModel(product_name="test")

        await RollbackToPreviousPatchVersion().apply(data=data, conn=conn)

        update_calls = [
            call
            for call in conn.sql.call_args_list
            if "UPDATE"
            in (str(call.args[0]) if call.args else str(call.kwargs.get("query", ""))).upper()
        ]
        rolled_back_params = [
            call.kwargs.get("params", call.args[1] if len(call.args) > 1 else ())
            for call in update_calls
        ]
        self.assertTrue(
            any("rolled_back" in params for params in rolled_back_params),
            msg="Expected an UPDATE setting status='rolled_back'",
        )

    async def test_rollback_reactivates_previous_row(self) -> None:
        """The previous row is updated to status 'active'."""
        conn = self._build_connection()
        data = ApplicationAndVersionNameModel(product_name="test")

        result = await RollbackToPreviousPatchVersion().apply(data=data, conn=conn)

        update_calls = [
            call
            for call in conn.sql.call_args_list
            if "UPDATE"
            in (str(call.args[0]) if call.args else str(call.kwargs.get("query", ""))).upper()
        ]
        update_params = [
            call.kwargs.get("params", call.args[1] if len(call.args) > 1 else ())
            for call in update_calls
        ]
        reactivate_params = [params for params in update_params if "active" in params]
        self.assertTrue(
            reactivate_params,
            msg="Expected an UPDATE setting status='active' on the previous row",
        )
        self.assertIsInstance(result, ApplicationAndVersionResponseModel)
        self.assertEqual(result.major, 1)
        self.assertEqual(result.minor, 2)
        self.assertEqual(result.patch, 2)

    async def test_rollback_raises_when_no_active_version(self) -> None:
        """A missing active version raises a ValueError."""
        conn = MagicMock()
        conn.sql.return_value = _make_result([("major",)], [])
        data = ApplicationAndVersionNameModel(product_name="missing")

        with self.assertRaises(ValueError):
            await RollbackToPreviousPatchVersion().apply(data=data, conn=conn)
