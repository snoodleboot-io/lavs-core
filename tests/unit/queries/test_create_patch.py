from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock

from app.models.requests.application_and_version_model import (
    ApplicationAndVersionNameModel,
)
from app.models.responses.application_and_version_response_model import (
    ApplicationAndVersionResponseModel,
)
from app.queries.patch_version.create_patch import CreatePatch


class TestCreatePatch(IsolatedAsyncioTestCase):
    """Unit tests asserting CreatePatch builds a parameterized INSERT."""

    def setUp(self) -> None:
        """Build a CreatePatch with a mocked latest-version query."""
        self._latest = ApplicationAndVersionResponseModel(
            product_name="test",
            major=1,
            minor=1,
            patch=1,
            id=1,
        )
        self._new_latest = ApplicationAndVersionResponseModel(
            product_name="test",
            major=1,
            minor=1,
            patch=2,
            id=2,
        )
        self._query = CreatePatch()
        # First execute() returns current latest, second returns the new latest.
        self._query._latest_version_query.execute = AsyncMock(
            side_effect=[self._latest, self._new_latest]
        )

    async def test_insert_uses_bound_placeholders_not_interpolation(self) -> None:
        """The INSERT SQL must use placeholders with no interpolated values."""
        data = ApplicationAndVersionNameModel(product_name="test", version="1.1.1")
        conn = MagicMock()

        await self._query.apply(data=data, conn=conn)

        conn.sql.assert_called_once()
        _, kwargs = conn.sql.call_args
        sql = kwargs["query"]
        params = kwargs["params"]

        # (a) SQL contains placeholders and no interpolated literal values.
        self.assertIn("?", sql)
        self.assertNotIn("'test'", sql)
        self.assertNotIn("VALUES (1,", sql)
        self.assertNotIn("VALUES (1 ,", sql)
        # The product name must not appear inline anywhere in the SQL text.
        self.assertNotIn("test", sql)
        # All four bound values are supplied as parameters.
        self.assertEqual(len(params), 4)
        self.assertIn("test", params)

    async def test_malicious_product_name_is_bound_not_interpolated(self) -> None:
        """A SQL-injection payload must be passed as a bound parameter only."""
        payload = "x'); DROP TABLE versions;--"
        malicious_latest = ApplicationAndVersionResponseModel(
            product_name=payload,
            major=1,
            minor=1,
            patch=1,
            id=1,
        )
        self._query._latest_version_query.execute = AsyncMock(
            side_effect=[malicious_latest, self._new_latest]
        )
        data = ApplicationAndVersionNameModel(product_name=payload, version="1.1.1")
        conn = MagicMock()

        await self._query.apply(data=data, conn=conn)

        conn.sql.assert_called_once()
        _, kwargs = conn.sql.call_args
        sql = kwargs["query"]
        params = kwargs["params"]

        # The payload must never be interpolated into the SQL string.
        self.assertNotIn("DROP TABLE", sql)
        self.assertNotIn(payload, sql)
        # It must be carried as a bound parameter instead.
        self.assertIn(payload, params)

    async def test_returns_new_latest_version(self) -> None:
        """Valid-input behavior is preserved: returns the refreshed latest version."""
        data = ApplicationAndVersionNameModel(product_name="test", version="1.1.1")
        conn = MagicMock()

        result = await self._query.apply(data=data, conn=conn)

        self.assertEqual(result, self._new_latest)

    async def test_missing_latest_version_raises(self) -> None:
        """When no base version exists the apply call raises ValueError."""
        self._query._latest_version_query.execute = AsyncMock(return_value=None)
        data = ApplicationAndVersionNameModel(product_name="test", version="1.1.1")
        conn = MagicMock()

        with self.assertRaises(ValueError):
            await self._query.apply(data=data, conn=conn)
        conn.sql.assert_not_called()
