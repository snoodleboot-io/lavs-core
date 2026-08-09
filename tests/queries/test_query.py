from unittest import IsolatedAsyncioTestCase

from app.models.requests.request_model import RequestModel
from app.queries.query import Query


class TestQuery(IsolatedAsyncioTestCase):
    """Behavior of the generic ``Query`` base class."""

    async def test_execute_raises_not_implemented(self) -> None:
        """The base ``Query`` has no ``apply`` and surfaces ``NotImplementedError``."""
        # Arrange
        query: Query[RequestModel] = Query()

        # Act / Assert
        with self.assertRaises(NotImplementedError):
            await query.execute(data=RequestModel())
