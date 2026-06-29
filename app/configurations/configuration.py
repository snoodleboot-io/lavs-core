"""Configuration management for the application.

This module provides configuration loading from YAML files and manages
database configuration settings.
"""

import os
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel

from app.configurations.root_dir import root_dir


class TableField(BaseModel):
    """Represents a database table field definition."""

    name: str
    type: str


class TableDefinition(BaseModel):
    """Represents a database table definition."""

    name: str
    fields: list[TableField]


class DatabaseTableConfig(BaseModel):
    """Configuration for database tables."""

    table: TableDefinition


class DuckDBConfig(BaseModel):
    """Configuration for DuckDB database."""

    database: str = "test.db"


class DatabaseConfig(BaseModel):
    """Root database configuration model."""

    database: DatabaseTableConfig
    duck_db: DuckDBConfig


class ApplicationConfig(BaseModel):
    """Application-level configuration."""

    version: int = 0
    application_name: str = "lavs-api"


def get_database_config_path() -> Path:
    """Get the path to the database configuration file.

    Returns:
        Path to the database.yaml configuration file.
    """
    return Path(root_dir()) / "configurations" / "database.yaml"


@lru_cache(maxsize=1)
def load_database_config() -> DatabaseConfig:
    """Load and cache the database configuration from database.yaml.

    This function uses caching to avoid re-reading the YAML file on each call.
    The cache can be cleared if needed by calling load_database_config.cache_clear().

    Returns:
        DatabaseConfig: The loaded database configuration.

    Raises:
        FileNotFoundError: If database.yaml is not found.
        yaml.YAMLError: If the YAML file is malformed.
    """
    config_path = get_database_config_path()
    if not config_path.exists():
        raise FileNotFoundError(f"Database configuration file not found: {config_path}")

    with open(config_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return DatabaseConfig.model_validate(data)


def get_duckdb_database_name() -> str:
    """Get the DuckDB database name from configuration.

    Returns:
        str: The database name from database.yaml, or "test.db" as default.
    """
    try:
        config = load_database_config()
        return config.duck_db.database
    except FileNotFoundError, AttributeError:
        return "test.db"


def get_database_path() -> str:
    """Get the full path to the database file.

    Returns:
        str: Full path to the database file.
    """
    db_name = get_duckdb_database_name()
    # If it's an absolute path, return as-is
    if os.path.isabs(db_name):
        return db_name
    # Otherwise, join with root directory
    return os.path.join(root_dir(), db_name)


class Configuration(BaseModel):
    """Stores basic application configuration.

    This class provides a unified interface for accessing both application
    and database configuration settings.
    """

    version: int = 0
    application_name: str = "lavs-api"

    @property
    def database_name(self) -> str:
        """Get the database name from database.yaml configuration.

        Returns:
            str: The configured database name.
        """
        return get_duckdb_database_name()

    @property
    def database_path(self) -> str:
        """Get the full path to the database file.

        Returns:
            str: Full path to the database file.
        """
        return get_database_path()

    @property
    def database_config(self) -> DatabaseConfig:
        """Get the full database configuration.

        Returns:
            DatabaseConfig: The loaded database configuration.
        """
        return load_database_config()


# Module-level instance for backwards compatibility
_configuration = Configuration()
