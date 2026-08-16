"""Unit tests for :class:`MssqlBackend` identity and DSN parsing."""

from app.backends.backend_kind import BackendKind
from app.backends.backend_settings import BackendSettings
from app.backends.mssql_backend import MssqlBackend
from app.connections.param_style import ParamStyle


class TestMssqlBackendIdentity:
    """The backend reports its kind and placeholder style."""

    def test_name_is_mssql(self) -> None:
        assert MssqlBackend().name is BackendKind.MSSQL

    def test_param_style_is_pyformat(self) -> None:
        assert MssqlBackend().param_style is ParamStyle.PYFORMAT


class TestMssqlBackendConnectionKwargs:
    """``connect`` builds pymssql kwargs from the settings (DSN preferred)."""

    def test_discrete_fields_become_server_kwargs(self) -> None:
        # Arrange
        settings = BackendSettings(
            mssql_host="db.internal",
            mssql_port=14330,
            mssql_db="lavs",
            mssql_user="svc",
            mssql_password="secret",
        )
        backend = MssqlBackend(settings)

        # Act
        kwargs = backend._connection_kwargs()

        # Assert
        assert kwargs["server"] == "db.internal"
        assert kwargs["port"] == 14330
        assert kwargs["database"] == "lavs"
        assert kwargs["user"] == "svc"
        assert kwargs["password"] == "secret"
        assert kwargs["autocommit"] is True

    def test_dsn_is_parsed_into_server_kwargs(self) -> None:
        # Arrange
        settings = BackendSettings(mssql_dsn="mssql://svc:secret@db.internal:14330/lavs")
        backend = MssqlBackend(settings)

        # Act
        kwargs = backend._connection_kwargs()

        # Assert
        assert kwargs["server"] == "db.internal"
        assert kwargs["port"] == 14330
        assert kwargs["user"] == "svc"
        assert kwargs["password"] == "secret"
        assert kwargs["database"] == "lavs"
        assert kwargs["autocommit"] is True

    def test_dialect_ddl_is_tsql(self) -> None:
        # Act
        ddl = MssqlBackend().dialect_ddl()

        # Assert
        assert "DATETIME2" in ddl
        assert "IF OBJECT_ID" in ddl
        assert "CREATE TABLE products" in ddl
