import traceback
from logging import getLogger
from typing import Any

import duckdb

from app.configurations.configuration import Configuration
from app.connections.connection_factory import ConnectionFactory
from app.models.requests.request_model import RequestModel
from app.models.responses.application_and_version_response_model import (
    ApplicationAndVersionResponseModel,
)
from app.models.responses.patch_response_model import PatchResponseModel


class Query[
    T: (
        ApplicationAndVersionResponseModel,
        PatchResponseModel,
        list[ApplicationAndVersionResponseModel],
    )
]:
    def __init__(self):
        self._logger = getLogger(Configuration().application_name)

    async def execute(
        self, data: RequestModel, connection: duckdb.DuckDBPyConnection | None = None
    ) -> T:
        """Execute the query against a database connection.

        When ``connection`` is provided (for example, the application-managed
        DuckDB connection opened by the FastAPI lifespan), it is reused
        directly rather than opening a fresh per-call connection. When no
        connection is supplied, a connection is opened via the factory
        context manager and closed when the call completes.

        Args:
            data: The request payload for this query.
            connection: An optional live database connection to reuse.

        Returns:
            The typed query result.
        """
        try:
            if connection is not None:
                result = await self.apply(data, connection)  # type: ignore[arg-type]
            else:
                with ConnectionFactory().retrieve(key="duckdb") as conn:
                    result = await self.apply(data, conn)  # type: ignore[arg-type]
        except Exception:
            self._logger.error(traceback.format_exc())
            raise

        return result

    async def apply(self, data: Any, conn: Any) -> T:
        raise NotImplementedError
