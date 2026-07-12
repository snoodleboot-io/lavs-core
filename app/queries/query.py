import traceback
from logging import getLogger
from typing import Any

from app.backends.backend_factory import BackendFactory
from app.configurations.configuration import Configuration
from app.connections.db_session import DbSession
from app.models.requests.request_model import RequestModel


class Query[T]:
    """Generic, connection-aware query executor.

    ``T`` is left unbounded so every resource lane (products, components,
    versions, the composite timeline, and ``list[...]`` of those response
    models) can specialise :class:`Query` without widening a constraint set on
    every new model. Subclasses implement :meth:`apply` and return a value of
    type ``T``.
    """

    def __init__(self):
        self._logger = getLogger(Configuration().application_name)

    async def execute(self, data: RequestModel, connection: DbSession | None = None) -> T:
        """Execute the query against a database session.

        When ``connection`` is provided (for example, the application-managed
        :class:`DbSession` opened by the FastAPI lifespan), it is reused directly
        rather than opening a fresh per-call session. When no session is
        supplied, one is opened via the configured backend and closed when the
        call completes.

        Args:
            data: The request payload for this query.
            connection: An optional live database session to reuse.

        Returns:
            The typed query result.
        """
        try:
            if connection is not None:
                result = await self.apply(data, connection)
            else:
                with BackendFactory().create().connect() as session:
                    result = await self.apply(data, session)
        except Exception:
            self._logger.error(traceback.format_exc())
            raise

        return result

    async def apply(self, data: Any, conn: Any) -> T:
        raise NotImplementedError
