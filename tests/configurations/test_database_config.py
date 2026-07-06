"""Tests for the config-driven database table manifest."""

from app.configurations.configuration import load_database_config


def test_database_config_lists_core_tables() -> None:
    """database.yaml must declare the products, components and versions tables."""
    # Act
    config = load_database_config()
    names = [table.name for table in config.database.tables]

    # Assert
    assert names == ["products", "components", "versions"]


def test_versions_table_declares_status_field() -> None:
    """The versions table manifest must include the status field."""
    # Act
    config = load_database_config()
    versions = next(t for t in config.database.tables if t.name == "versions")
    field_names = {field.name for field in versions.fields}

    # Assert
    assert "status" in field_names
    assert "component_id" in field_names
