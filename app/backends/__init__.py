"""Pluggable persistence backends (DuckDB today; Postgres and others to come).

A :class:`~app.backends.backend.Backend` hides dialect and driver details behind
``connect`` / ``init_schema``, yielding a uniform
:class:`~app.connections.db_session.DbSession` to the query layer. The concrete
backend is selected from configuration by
:class:`~app.backends.backend_factory.BackendFactory`.
"""
