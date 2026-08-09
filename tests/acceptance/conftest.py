"""Fixtures for the LAVS acceptance suite.

Provides a function-scoped, isolated DuckDB-backed TestClient against ``app.main:app``.
The fixture mirrors the integration conftest's isolation approach so acceptance tests
exercise the real application wiring (routers, models, queries) end to end.
"""

import os
import pathlib
import shutil
import tempfile
import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

# Repository root (tests/acceptance/conftest.py -> repo root is two parents up).
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_DDL_PATH = _REPO_ROOT / "app" / "database" / "duckdb" / "ddl.sql"


@pytest.fixture(scope="function")
def test_db() -> Iterator[str]:
    """Create and tear down an isolated DuckDB database for a single test.

    Yields:
        The filesystem path to the temporary test database.
    """
    temp_dir = tempfile.mkdtemp()
    test_db_path = os.path.join(temp_dir, f"acceptance_{uuid.uuid4().hex[:8]}.db")

    try:
        import duckdb

        connection = duckdb.connect(test_db_path)
        with open(_DDL_PATH) as stream:
            ddl = stream.read()
        connection.execute(query=ddl)
        connection.close()

        import app.configurations.configuration as config_module

        original_get_database_path = config_module.get_database_path
        original_get_duckdb_database_name = config_module.get_duckdb_database_name

        config_module.get_database_path = lambda: test_db_path
        config_module.get_duckdb_database_name = lambda: test_db_path
        config_module.load_database_config.cache_clear()

        yield test_db_path
    finally:
        config_module.get_database_path = original_get_database_path
        config_module.get_duckdb_database_name = original_get_duckdb_database_name
        config_module.load_database_config.cache_clear()
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="function")
def client(test_db: str) -> Iterator[TestClient]:
    """Provide a FastAPI ``TestClient`` bound to an isolated test database.

    The client is entered as a context manager so the application ``lifespan`` runs
    (opening the managed DuckDB connection used by ``/ready`` and the query layer).

    Args:
        test_db: Path to the isolated test database (injected).

    Yields:
        A ``TestClient`` for the LAVS application with lifespan active.
    """
    from app.main import app

    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
