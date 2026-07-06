"""Pytest configuration for integration tests.

This module provides fixtures for setting up and tearing down test databases
for integration tests.
"""

import os
import shutil
import tempfile
import uuid

import pytest
from fastapi.testclient import TestClient

# ``duckdb`` is no longer imported directly: schema setup goes through the
# config-driven ``DatabaseManager`` so tests exercise the real init path.


@pytest.fixture(scope="function")
def test_db():
    """Fixture that creates and tears down a test database for each test.

    This fixture:
    1. Creates a temporary directory with a unique database file
    2. Patches the configuration module to use the test database
    3. Creates the database tables
    4. Yields control to the test
    5. Drops the tables and closes the database connection
    6. Cleans up the temporary directory

    Yields:
        str: The path to the test database file.
    """
    # Create a temporary directory for the test database
    temp_dir = tempfile.mkdtemp()
    # Use unique filename to avoid any caching issues
    test_db_path = os.path.join(temp_dir, f"test_{uuid.uuid4().hex[:8]}.db")

    try:
        # Patch the configuration at multiple levels to ensure isolation
        import app.configurations.configuration as config_module
        from app.connections import connection_factory
        from app.database.database_manager import DatabaseManager

        # Store original functions
        original_get_database_path = config_module.get_database_path
        original_get_duckdb_database_name = config_module.get_duckdb_database_name

        # Patch the functions
        config_module.get_database_path = lambda: test_db_path
        config_module.get_duckdb_database_name = lambda: test_db_path

        # Also patch the ConnectionFactory if it caches anything
        original_factory_init = connection_factory.ConnectionFactory.__init__

        def patched_init(self, config=None):
            original_factory_init(self, config)

        connection_factory.ConnectionFactory.__init__ = patched_init

        # Clear any cached configuration
        config_module.load_database_config.cache_clear()

        # Initialise the schema through the real, config-driven init path so the
        # tests exercise the same machinery the application uses.
        DatabaseManager.create_tables()

        yield test_db_path
    finally:
        # Tear the schema down through the same config-driven path.
        try:
            DatabaseManager.drop_tables()
        except Exception:
            pass

        # Restore original functions
        config_module.get_database_path = original_get_database_path
        config_module.get_duckdb_database_name = original_get_duckdb_database_name
        connection_factory.ConnectionFactory.__init__ = original_factory_init

        # Clear any cached configuration
        config_module.load_database_config.cache_clear()

        # Clean up temp directory
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass


@pytest.fixture(scope="function")
def client(test_db: str) -> TestClient:
    """Fixture that provides a FastAPI TestClient with a test database.

    Args:
        test_db: The test database path (injected by test_db fixture).

    Returns:
        TestClient: A FastAPI test client for making HTTP requests.
    """
    from app.main import app

    return TestClient(app)
