"""Unit tests for :class:`BackendKind` and :class:`BackendSettings` parsing."""

import pytest

from app.backends.backend_kind import BackendKind
from app.backends.backend_settings import BackendSettings


class TestBackendSelection:
    """``LAVS_DB_BACKEND`` selects the backend, defaulting to DuckDB."""

    def test_defaults_to_duckdb_when_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Arrange
        monkeypatch.delenv("LAVS_DB_BACKEND", raising=False)

        # Act / Assert
        assert BackendSettings().backend() is BackendKind.DUCKDB

    def test_env_selects_postgres(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Arrange
        monkeypatch.setenv("LAVS_DB_BACKEND", "postgres")

        # Act / Assert
        assert BackendSettings().backend() is BackendKind.POSTGRES

    def test_env_is_case_insensitive(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Arrange
        monkeypatch.setenv("LAVS_DB_BACKEND", "  PostgreS  ")

        # Act / Assert
        assert BackendSettings().backend() is BackendKind.POSTGRES

    def test_unknown_token_falls_back_to_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Arrange
        monkeypatch.setenv("LAVS_DB_BACKEND", "cassandra")

        # Act / Assert
        assert BackendSettings().backend() is BackendKind.DUCKDB

    def test_constructor_override_wins_over_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Arrange
        monkeypatch.setenv("LAVS_DB_BACKEND", "duckdb")

        # Act / Assert
        assert BackendSettings(backend=BackendKind.POSTGRES).backend() is BackendKind.POSTGRES


class TestPostgresAccessors:
    """The Postgres connection accessors read env with sensible defaults."""

    def test_discrete_fields_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Arrange
        monkeypatch.setenv("LAVS_PG_HOST", "db.internal")
        monkeypatch.setenv("LAVS_PG_PORT", "6543")
        monkeypatch.setenv("LAVS_PG_DB", "lavs")
        monkeypatch.setenv("LAVS_PG_USER", "svc")
        monkeypatch.setenv("LAVS_PG_PASSWORD", "secret")
        monkeypatch.delenv("LAVS_PG_DSN", raising=False)

        # Act
        settings = BackendSettings()

        # Assert
        assert settings.pg_host() == "db.internal"
        assert settings.pg_port() == 6543
        assert settings.pg_db() == "lavs"
        assert settings.pg_user() == "svc"
        assert settings.pg_password() == "secret"
        assert settings.pg_dsn() is None

    def test_defaults_when_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Arrange
        for key in (
            "LAVS_PG_DSN",
            "LAVS_PG_HOST",
            "LAVS_PG_PORT",
            "LAVS_PG_DB",
            "LAVS_PG_USER",
            "LAVS_PG_PASSWORD",
        ):
            monkeypatch.delenv(key, raising=False)

        # Act
        settings = BackendSettings()

        # Assert
        assert settings.pg_host() == "localhost"
        assert settings.pg_port() == 5432
        assert settings.pg_db() is None
        assert settings.pg_user() is None
        assert settings.pg_password() is None

    def test_dsn_is_read_when_present(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Arrange
        monkeypatch.setenv("LAVS_PG_DSN", "postgresql://svc:secret@db/lavs")

        # Act / Assert
        assert BackendSettings().pg_dsn() == "postgresql://svc:secret@db/lavs"
