"""Integration tests for database connection migration to secure utilities."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.pool import NullPool

from tripsage_core.database.connection import (
    create_secure_async_engine,
    get_database_session,
    get_engine_for_testing,
    test_connection,
)
from tripsage_core.utils.connection_utils import (
    DatabaseValidationError,
)
from tripsage_core.utils.url_converters import DatabaseURLConverter


class TestDatabaseMigration:
    """Test database connection migration scenarios."""

    @pytest.fixture
    def mock_settings(self):
        """Mock settings for testing."""
        settings = MagicMock()
        settings.database_url = "https://test-project.supabase.co"
        settings.database_service_key.get_secret_value.return_value = "test-service-key"
        settings.database_public_key.get_secret_value.return_value = "test-public-key"
        settings.debug = False
        return settings

    @pytest.fixture
    def mock_converter(self):
        """Mock URL converter."""
        converter = MagicMock(spec=DatabaseURLConverter)
        converter.supabase_to_postgres.return_value = (
            "postgresql://postgres:test-key@test-project.supabase.co:5432/postgres?sslmode=require"
        )
        converter.is_postgres_url.return_value = True
        converter.is_supabase_url.side_effect = lambda url: url.startswith("https://")
        return converter

    @pytest.mark.asyncio
    async def test_secure_engine_creation_with_supabase_url(self, mock_settings):
        """Test creating engine with Supabase URL converts to PostgreSQL."""
        with patch("tripsage_core.database.connection.get_settings", return_value=mock_settings):
            with patch("tripsage_core.database.connection.create_async_engine") as mock_create:
                with patch("tripsage_core.database.connection.get_connection_manager") as mock_manager:
                    # Setup mocks
                    mock_engine = AsyncMock()
                    mock_create.return_value = mock_engine

                    mock_conn_mgr = MagicMock()
                    mock_creds = MagicMock()
                    mock_creds.to_connection_string.return_value = "postgresql://postgres:test@localhost:5432/test"
                    mock_creds.database = "postgres"
                    mock_creds.hostname = "test-project.supabase.co"

                    mock_conn_mgr.parse_and_validate_url = AsyncMock(return_value=mock_creds)
                    mock_manager.return_value = mock_conn_mgr

                    # Test engine creation
                    await create_secure_async_engine(
                        "https://test-project.supabase.co",
                        pool_size=5,
                        echo=True,
                    )

                    # Verify conversion happened
                    mock_conn_mgr.parse_and_validate_url.assert_called_once()
                    call_url = mock_conn_mgr.parse_and_validate_url.call_args[0][0]
                    assert "postgresql://" in call_url
                    assert "test-project.supabase.co" in call_url

                    # Verify engine created with async driver
                    mock_create.assert_called_once()
                    engine_url = mock_create.call_args[0][0]
                    assert "postgresql+asyncpg://" in engine_url

    @pytest.mark.asyncio
    async def test_secure_engine_creation_with_postgres_url(self):
        """Test creating engine with PostgreSQL URL."""
        postgres_url = "postgresql://user:pass@localhost:5432/testdb"

        with patch("tripsage_core.database.connection.create_async_engine") as mock_create:
            with patch("tripsage_core.database.connection.get_connection_manager") as mock_manager:
                # Setup mocks
                mock_engine = AsyncMock()
                mock_create.return_value = mock_engine

                mock_conn_mgr = MagicMock()
                mock_creds = MagicMock()
                mock_creds.to_connection_string.return_value = postgres_url
                mock_creds.database = "testdb"
                mock_creds.hostname = "localhost"

                mock_conn_mgr.parse_and_validate_url = AsyncMock(return_value=mock_creds)
                mock_manager.return_value = mock_conn_mgr

                # Test engine creation
                await create_secure_async_engine(postgres_url)

                # Verify URL was validated
                mock_conn_mgr.parse_and_validate_url.assert_called_once_with(postgres_url)

                # Verify engine created with asyncpg
                mock_create.assert_called_once()
                engine_url = mock_create.call_args[0][0]
                assert "postgresql+asyncpg://" in engine_url

    @pytest.mark.asyncio
    async def test_secure_engine_validation_failure(self):
        """Test engine creation fails on validation error."""
        with patch("tripsage_core.database.connection.get_connection_manager") as mock_manager:
            mock_conn_mgr = MagicMock()
            mock_conn_mgr.parse_and_validate_url = AsyncMock(
                side_effect=DatabaseValidationError("Connection validation failed")
            )
            mock_manager.return_value = mock_conn_mgr

            with pytest.raises(DatabaseValidationError) as exc_info:
                await create_secure_async_engine("postgresql://bad:url@host/db")

            assert "Connection validation failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_checkpoint_manager_migration(self, mock_settings, mock_converter):
        """Test checkpoint manager uses secure URL conversion."""
        with patch(
            "tripsage.orchestration.checkpoint_manager.get_settings",
            return_value=mock_settings,
        ):
            with patch(
                "tripsage.orchestration.checkpoint_manager.DatabaseURLConverter",
                return_value=mock_converter,
            ):
                with patch(
                    "tripsage.orchestration.checkpoint_manager.SecureDatabaseConnectionManager"
                ) as mock_mgr_class:
                    # Setup mock manager
                    mock_manager = MagicMock()
                    mock_manager.parse_and_validate_url = AsyncMock()
                    mock_mgr_class.return_value = mock_manager

                    from tripsage.orchestration.checkpoint_manager import (
                        SupabaseCheckpointManager,
                    )

                    manager = SupabaseCheckpointManager()
                    conn_string = manager._build_connection_string()

                    # Verify secure conversion was used
                    mock_converter.supabase_to_postgres.assert_called_once_with(
                        mock_settings.database_url,
                        "test-service-key",
                        use_pooler=False,
                        sslmode="require",
                    )

                    # Verify connection string is PostgreSQL format
                    assert conn_string.startswith("postgresql://")
                    assert "sslmode=require" in conn_string

    @pytest.mark.asyncio
    async def test_database_session_with_secure_connection(self, mock_settings):
        """Test database session uses secure connection."""
        with patch("tripsage_core.database.connection.get_settings", return_value=mock_settings):
            with patch("tripsage_core.database.connection.get_engine") as mock_get_engine:
                with patch("tripsage_core.database.connection.async_sessionmaker") as mock_sessionmaker:
                    # Setup mocks
                    mock_engine = MagicMock()
                    mock_get_engine.return_value = mock_engine

                    mock_session = AsyncMock()
                    mock_session_factory = MagicMock()
                    mock_session_factory.__aenter__ = AsyncMock(return_value=mock_session)
                    mock_session_factory.__aexit__ = AsyncMock()
                    mock_sessionmaker.return_value.return_value = mock_session_factory

                    # Test session creation
                    async with get_database_session() as session:
                        assert session == mock_session

                    # Verify secure engine was used
                    mock_get_engine.assert_called_once()
                    mock_sessionmaker.assert_called_once_with(
                        mock_engine,
                        class_=AsyncSession,
                        expire_on_commit=False,
                        autoflush=False,
                        autocommit=False,
                    )

    @pytest.mark.asyncio
    async def test_connection_test_with_extensions(self, mock_settings):
        """Test connection validation checks for required extensions."""
        with patch("tripsage_core.database.connection.get_database_session") as mock_session_context:
            # Setup mock session
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar.return_value = 1
            mock_result.one.return_value = MagicMock(
                database="postgres",
                user="postgres",
                version="PostgreSQL 14.5",
                is_replica=False,
            )

            # Mock extension query
            mock_ext_result = MagicMock()
            mock_ext_result.__iter__ = MagicMock(
                return_value=iter(
                    [
                        MagicMock(extname="vector", extversion="0.4.0"),
                        MagicMock(extname="uuid-ossp", extversion="1.1"),
                    ]
                )
            )

            mock_session.execute = AsyncMock(side_effect=[mock_result, mock_result, mock_ext_result])

            # Setup context manager
            mock_session_context.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_context.return_value.__aexit__ = AsyncMock()

            # Test connection
            result = await test_connection()

            assert result is True

            # Verify extension check was performed
            assert mock_session.execute.call_count == 3
            ext_call = mock_session.execute.call_args_list[2]
            assert "pg_extension" in str(ext_call)
            assert "vector" in str(ext_call)

    @pytest.mark.asyncio
    async def test_test_engine_creation(self):
        """Test creating engine for testing with NullPool."""
        test_url = "postgresql://test:test@localhost:5432/test"

        with patch("tripsage_core.database.connection.create_secure_async_engine") as mock_create:
            mock_engine = AsyncMock()
            mock_engine.dispose = AsyncMock()
            mock_create.return_value = mock_engine

            async with get_engine_for_testing(test_url) as engine:
                assert engine == mock_engine

            # Verify NullPool was used
            mock_create.assert_called_once_with(
                test_url,
                poolclass=NullPool,
                echo=True,
            )

            # Verify engine was disposed
            mock_engine.dispose.assert_called_once()

    @pytest.mark.asyncio
    async def test_security_features_in_connection(self):
        """Test security features are properly configured."""
        postgres_url = "postgresql://user:password@host:5432/db?sslmode=require"

        with patch("tripsage_core.database.connection.create_async_engine") as mock_create:
            with patch("tripsage_core.database.connection.get_connection_manager") as mock_manager:
                # Setup mocks
                mock_engine = AsyncMock()
                mock_create.return_value = mock_engine

                mock_conn_mgr = MagicMock()
                mock_creds = MagicMock()
                mock_creds.to_connection_string.return_value = postgres_url
                mock_creds.database = "db"
                mock_creds.hostname = "host"
                mock_creds.query_params = {"sslmode": "require"}

                mock_conn_mgr.parse_and_validate_url = AsyncMock(return_value=mock_creds)
                mock_manager.return_value = mock_conn_mgr

                # Test engine creation
                await create_secure_async_engine(
                    postgres_url,
                    pool_pre_ping=True,
                    pool_size=10,
                )

                # Verify security settings
                mock_create.assert_called_once()
                call_kwargs = mock_create.call_args[1]

                # Check pool settings
                assert call_kwargs["pool_pre_ping"] is True
                assert call_kwargs["pool_size"] == 10
                assert call_kwargs["pool_recycle"] == 3600
                assert call_kwargs["pool_timeout"] == 30

                # Check connect args
                connect_args = call_kwargs["connect_args"]
                assert connect_args["server_settings"]["application_name"] == "tripsage"
                assert connect_args["command_timeout"] == 60
                assert connect_args["timeout"] == 10
