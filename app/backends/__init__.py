"""Pluggable persistence backends (DuckDB today; Postgres and others to come).

A :class:`~app.backends.backend.Backend` hides dialect and driver details behind
``connect`` / ``init_schema``, yielding a uniform
:class:`~app.connections.db_session.DbSession` to the query layer. The concrete
backend is selected from configuration by
:class:`~app.backends.backend_factory.BackendFactory`.

Importing this package registers every optional backend's builder on the factory
so a configured ``LAVS_DB_BACKEND=postgres`` (or ``mysql`` / ``mssql``) resolves
without any other module having to reach for the concrete class. DuckDB is
registered by the factory itself; Postgres, MySQL, and SQL Server are registered
here (the seam described on :meth:`BackendFactory.register`).
"""

from app.backends.backend_factory import BackendFactory
from app.backends.backend_kind import BackendKind
from app.backends.mssql_backend import MssqlBackend
from app.backends.mysql_backend import MySqlBackend
from app.backends.postgres_backend import PostgresBackend

BackendFactory.register(BackendKind.POSTGRES, lambda settings: PostgresBackend(settings))
BackendFactory.register(BackendKind.MYSQL, lambda settings: MySqlBackend(settings))
BackendFactory.register(BackendKind.MSSQL, lambda settings: MssqlBackend(settings))
