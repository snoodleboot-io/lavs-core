"""The backend interface the query layer depends on.

A :class:`Backend` hides the concrete driver and SQL dialect behind three
operations:

* :meth:`connect` — open a driver connection and yield it wrapped in a uniform
  :class:`~app.connections.db_session.DbSession`, closing it on exit;
* :meth:`init_schema` — materialise the dialect's schema on a session;
* :meth:`dialect_ddl` — the dialect-specific DDL the schema is built from.

Adding a new backend (for example the R1 ``PostgresBackend``) means subclassing
this and supplying :attr:`name`, :attr:`param_style`, :meth:`connect`, and
:meth:`dialect_ddl`. :meth:`init_schema` has a default that runs the whole DDL
script through the session; a dialect whose driver rejects multi-statement
execution (psycopg does) overrides it to split the script.
"""

from abc import ABC, abstractmethod
from contextlib import AbstractContextManager

from app.backends.backend_kind import BackendKind
from app.connections.db_session import DbSession
from app.connections.param_style import ParamStyle


class Backend(ABC):
    """Abstract persistence backend yielding uniform :class:`DbSession` handles."""

    @property
    @abstractmethod
    def name(self) -> BackendKind:
        """Return the backend's identifier."""
        raise NotImplementedError

    @property
    @abstractmethod
    def param_style(self) -> ParamStyle:
        """Return the placeholder style the backend's driver expects."""
        raise NotImplementedError

    @abstractmethod
    def connect(self) -> AbstractContextManager[DbSession]:
        """Open a connection and yield it as a :class:`DbSession`.

        The returned context manager owns the underlying driver connection and
        closes it on exit.

        Returns:
            A context manager yielding a live :class:`DbSession`.
        """
        raise NotImplementedError

    @abstractmethod
    def dialect_ddl(self) -> str:
        """Return the dialect-specific schema DDL script."""
        raise NotImplementedError

    def init_schema(self, session: DbSession) -> None:
        """Materialise the schema on an open session by running the dialect DDL.

        The default runs the entire :meth:`dialect_ddl` script in one call, which
        DuckDB supports. Backends whose driver rejects multi-statement execution
        override this.

        Args:
            session: A live session to run the DDL on.
        """
        session.execute(self.dialect_ddl())
