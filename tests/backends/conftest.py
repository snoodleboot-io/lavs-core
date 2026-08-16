"""Fixtures for the PostgreSQL parity suite.

These fixtures stand up a disposable real PostgreSQL and point the application's
:class:`~app.backends.backend_factory.BackendFactory` at it, so the *identical*
routers, queries, and models the DuckDB suite exercises run against real PG.

* :func:`postgres_container` (session-scoped) starts one throwaway
  ``postgres:17-alpine`` container for the whole run and tears it down at the
  end. When Docker (or the image) is unavailable it ``pytest.skip``s with a clear
  reason rather than passing silently.
* :func:`pg_env` (function-scoped) resets the database to a pristine ``public``
  schema and exports the ``LAVS_DB_BACKEND`` / ``LAVS_PG_*`` environment so each
  test starts against a clean database and is independent — the application's
  lifespan re-runs ``init_schema`` on that clean database.

The container is shared for speed but every test gets a freshly emptied schema,
satisfying the "fresh, independent, ``init_schema``-on-clean" requirement without
paying a container start per test.
"""

import os
from collections.abc import Iterator
from typing import Any, NoReturn

import psycopg
import pymssql
import pymysql
import pytest

#: The disposable PostgreSQL image the parity suite runs against.
_PG_IMAGE = "postgres:17-alpine"
#: The container-internal port PostgreSQL listens on.
_PG_INTERNAL_PORT = 5432

#: The disposable MySQL image the parity suite runs against.
_MYSQL_IMAGE = "mysql:8.4"
#: The container-internal port MySQL listens on.
_MYSQL_INTERNAL_PORT = 3306

#: The disposable SQL Server image the parity suite runs against.
_MSSQL_IMAGE = "mcr.microsoft.com/mssql/server:2022-latest"
#: The container-internal port SQL Server listens on.
_MSSQL_INTERNAL_PORT = 1433


def _containers_unavailable(reason: str) -> NoReturn:
    """Skip when containers are unavailable locally, but **fail in CI**.

    Multi-backend parity is the exit criterion for every non-DuckDB backend, so
    it must actually execute in CI — a silently skipped parity suite there would
    give a false green. GitHub Actions always sets ``CI``, so when it is set an
    unavailable container is a hard failure; local dev without Docker still skips
    gracefully.

    Args:
        reason: Why the container could not start.

    Raises:
        Failed: In CI (``CI`` set) — parity must not be skipped.
        Skipped: Locally — Docker/the image is simply unavailable.
    """
    if os.environ.get("CI"):
        pytest.fail(f"backend parity suite must run in CI but {reason}")
    pytest.skip(reason)


@pytest.fixture(scope="session")
def postgres_container() -> Iterator[Any]:
    """Start one disposable PostgreSQL container for the session, or skip.

    Yields:
        The running ``PostgresContainer``.
    """
    try:
        from testcontainers.postgres import PostgresContainer
    except ImportError as exc:  # pragma: no cover - dependency is declared
        _containers_unavailable(f"testcontainers is not installed: {exc}")

    try:
        container = PostgresContainer(_PG_IMAGE)
        container.start()
    except Exception as exc:  # Docker daemon or image pull unavailable.
        _containers_unavailable(
            f"Docker/PostgreSQL testcontainer is unavailable (cannot start {_PG_IMAGE}): {exc}"
        )

    try:
        yield container
    finally:
        container.stop()


def _connection_kwargs(container: Any) -> dict[str, Any]:
    """Return psycopg connection kwargs for the running container."""
    return {
        "host": container.get_container_host_ip(),
        "port": int(container.get_exposed_port(_PG_INTERNAL_PORT)),
        "dbname": container.dbname,
        "user": container.username,
        "password": container.password,
    }


def _reset_public_schema(container: Any) -> None:
    """Drop and recreate the ``public`` schema so the next test sees a clean DB."""
    with psycopg.connect(**_connection_kwargs(container)) as connection:
        connection.autocommit = True
        connection.execute("DROP SCHEMA public CASCADE")
        connection.execute("CREATE SCHEMA public")


@pytest.fixture()
def pg_env(postgres_container: Any, monkeypatch: pytest.MonkeyPatch) -> Iterator[Any]:
    """Reset the database and select the Postgres backend for one test.

    Args:
        postgres_container: The session container (injected).
        monkeypatch: Pytest's env patcher (auto-undone on teardown).

    Yields:
        The running container, for tests that need its connection parameters.
    """
    _reset_public_schema(postgres_container)

    kwargs = _connection_kwargs(postgres_container)
    monkeypatch.setenv("LAVS_DB_BACKEND", "postgres")
    monkeypatch.setenv("LAVS_PG_HOST", str(kwargs["host"]))
    monkeypatch.setenv("LAVS_PG_PORT", str(kwargs["port"]))
    monkeypatch.setenv("LAVS_PG_DB", str(kwargs["dbname"]))
    monkeypatch.setenv("LAVS_PG_USER", str(kwargs["user"]))
    monkeypatch.setenv("LAVS_PG_PASSWORD", str(kwargs["password"]))

    yield postgres_container


@pytest.fixture(scope="session")
def mysql_container() -> Iterator[Any]:
    """Start one disposable MySQL container for the session, or skip.

    Yields:
        The running ``MySqlContainer``.
    """
    try:
        from testcontainers.mysql import MySqlContainer
    except ImportError as exc:  # pragma: no cover - dependency is declared
        _containers_unavailable(f"testcontainers is not installed: {exc}")

    try:
        container = MySqlContainer(_MYSQL_IMAGE)
        container.start()
    except Exception as exc:  # Docker daemon or image pull unavailable.
        _containers_unavailable(
            f"Docker/MySQL testcontainer is unavailable (cannot start {_MYSQL_IMAGE}): {exc}"
        )

    try:
        yield container
    finally:
        container.stop()


def _mysql_connection_kwargs(container: Any) -> dict[str, Any]:
    """Return PyMySQL connection kwargs for the running container."""
    return {
        "host": container.get_container_host_ip(),
        "port": int(container.get_exposed_port(_MYSQL_INTERNAL_PORT)),
        "database": container.dbname,
        "user": container.username,
        "password": container.password,
    }


def _reset_mysql_database(container: Any) -> None:
    """Drop every table in the database so the next test sees a clean schema.

    MySQL scopes grants to a database, so dropping and recreating the database
    would strip the app user's privileges; instead every table is dropped with
    foreign-key checks disabled, leaving an empty schema the app re-materialises.
    """
    kwargs = _mysql_connection_kwargs(container)
    connection = pymysql.connect(**kwargs)
    try:
        connection.autocommit(True)
        cursor = connection.cursor()
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        cursor.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = %s",
            (kwargs["database"],),
        )
        tables = [row[0] for row in cursor.fetchall()]
        for table in tables:
            cursor.execute(f"DROP TABLE IF EXISTS `{table}`")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
    finally:
        connection.close()


@pytest.fixture()
def mysql_env(mysql_container: Any, monkeypatch: pytest.MonkeyPatch) -> Iterator[Any]:
    """Reset the database and select the MySQL backend for one test.

    Args:
        mysql_container: The session container (injected).
        monkeypatch: Pytest's env patcher (auto-undone on teardown).

    Yields:
        The running container, for tests that need its connection parameters.
    """
    _reset_mysql_database(mysql_container)

    kwargs = _mysql_connection_kwargs(mysql_container)
    monkeypatch.setenv("LAVS_DB_BACKEND", "mysql")
    monkeypatch.setenv("LAVS_MYSQL_HOST", str(kwargs["host"]))
    monkeypatch.setenv("LAVS_MYSQL_PORT", str(kwargs["port"]))
    monkeypatch.setenv("LAVS_MYSQL_DB", str(kwargs["database"]))
    monkeypatch.setenv("LAVS_MYSQL_USER", str(kwargs["user"]))
    monkeypatch.setenv("LAVS_MYSQL_PASSWORD", str(kwargs["password"]))

    yield mysql_container


@pytest.fixture(scope="session")
def mssql_container() -> Iterator[Any]:
    """Start one disposable SQL Server container for the session, or skip.

    Yields:
        The running ``SqlServerContainer``.
    """
    try:
        from testcontainers.mssql import SqlServerContainer
    except ImportError as exc:  # pragma: no cover - dependency is declared
        _containers_unavailable(f"testcontainers is not installed: {exc}")

    try:
        container = SqlServerContainer(_MSSQL_IMAGE)
        container.start()
    except Exception as exc:  # Docker daemon or image pull unavailable.
        _containers_unavailable(
            f"Docker/SQL Server testcontainer is unavailable (cannot start {_MSSQL_IMAGE}): {exc}"
        )

    try:
        yield container
    finally:
        container.stop()


def _mssql_connection_kwargs(container: Any) -> dict[str, Any]:
    """Return pymssql connection kwargs for the running container."""
    return {
        "server": container.get_container_host_ip(),
        "port": int(container.get_exposed_port(_MSSQL_INTERNAL_PORT)),
        "database": container.dbname,
        "user": container.username,
        "password": container.password,
    }


def _reset_mssql_database(container: Any) -> None:
    """Drop every user table so the next test sees a clean schema.

    SQL Server refuses to drop a table another table's foreign key references, so
    every foreign key is dropped first, then every user table — leaving an empty
    schema the app re-materialises via ``init_schema``.
    """
    kwargs = _mssql_connection_kwargs(container)
    connection = pymssql.connect(autocommit=True, **kwargs)
    try:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT OBJECT_SCHEMA_NAME(parent_object_id), "
            "OBJECT_NAME(parent_object_id), name FROM sys.foreign_keys"
        )
        foreign_keys = cursor.fetchall()
        for schema, table, name in foreign_keys:
            cursor.execute(f"ALTER TABLE [{schema}].[{table}] DROP CONSTRAINT [{name}]")
        cursor.execute("SELECT OBJECT_SCHEMA_NAME(object_id), name FROM sys.tables")
        tables = cursor.fetchall()
        for schema, table in tables:
            cursor.execute(f"DROP TABLE [{schema}].[{table}]")
    finally:
        connection.close()


@pytest.fixture()
def mssql_env(mssql_container: Any, monkeypatch: pytest.MonkeyPatch) -> Iterator[Any]:
    """Reset the database and select the SQL Server backend for one test.

    Args:
        mssql_container: The session container (injected).
        monkeypatch: Pytest's env patcher (auto-undone on teardown).

    Yields:
        The running container, for tests that need its connection parameters.
    """
    _reset_mssql_database(mssql_container)

    kwargs = _mssql_connection_kwargs(mssql_container)
    monkeypatch.setenv("LAVS_DB_BACKEND", "mssql")
    monkeypatch.setenv("LAVS_MSSQL_HOST", str(kwargs["server"]))
    monkeypatch.setenv("LAVS_MSSQL_PORT", str(kwargs["port"]))
    monkeypatch.setenv("LAVS_MSSQL_DB", str(kwargs["database"]))
    monkeypatch.setenv("LAVS_MSSQL_USER", str(kwargs["user"]))
    monkeypatch.setenv("LAVS_MSSQL_PASSWORD", str(kwargs["password"]))

    yield mssql_container
