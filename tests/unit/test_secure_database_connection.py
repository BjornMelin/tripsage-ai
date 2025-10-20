"""Unit tests for database connection module (final-only)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.pool import NullPool, QueuePool

from tripsage_core.database.connection import (
    Base,
    close_connections,
    create_secure_async_engine,
    get_database_session,
    get_engine,
    get_engine_for_testing,
    get_session_factory,
    test_connection,
)
from tripsage_core.utils.connection_utils import (
    DatabaseURLParsingError,
    DatabaseValidationError,
)


class TestDatabaseConnection:
    """Test secure database connection functionality."""

    @pytest.fixture
    def mock_settings(self):
        """Mock settings for testing."""
        settings = MagicMock()
        settings.database_url = "https://test-project.supabase.co"
        settings.database_service_key.get_secret_value.return_value = "test-key"
        settings.effective_postgres_url = (
            "postgresql://postgres:test-key@test.supabase.co:5432/postgres"
        )
        settings.debug = False
        return settings

    @pytest.fixture
    def mock_credentials(self):
        """Mock connection credentials."""
        creds = MagicMock()
        creds.to_connection_string.return_value = "postgresql://user:pass@host:5432/db"
        creds.database = "db"
        creds.hostname = "host"
        creds.port = 5432
        creds.username = "user"
        creds.password = "pass"
        creds.query_params = {"sslmode": "require"}
        return creds

    def test_base_declarative_class(self):
        """Test Base declarative class is properly defined."""
        # DeclarativeBase itself doesn't define __tablename__; subclasses do.
        assert hasattr(Base, "metadata")

        # Should be usable as base for models
        from sqlalchemy import Integer
        from sqlalchemy.orm import Mapped, mapped_column

        class TestModel(Base):
            """Test model for testing."""

            __tablename__ = "test"
            id: Mapped[int] = mapped_column(Integer, primary_key=True)

        assert TestModel.__tablename__ == "test"

    @pytest.mark.asyncio
    async def test_create_secure_async_engine_with_supabase(
        self, mock_settings, mock_credentials
    ):
        """Test engine creation with Supabase URL."""
        with (
            patch(
                "tripsage_core.database.connection.get_settings",
                return_value=mock_settings,
            ),
            patch(
                "tripsage_core.database.connection.DatabaseURLDetector"
            ) as mock_detector,
            patch(
                "tripsage_core.database.connection.DatabaseURLConverter"
            ) as mock_converter,
            patch(
                "tripsage_core.database.connection.create_async_engine"
            ) as mock_create,
        ):
            # Setup mocks
            mock_detector.return_value.detect_url_type.return_value = {
                "type": "supabase"
            }

            mock_converter.return_value.supabase_to_postgres.return_value = (
                "postgresql://postgres:key@test.supabase.co:5432/postgres"
            )

            mock_engine = AsyncMock()
            # Configure begin() to be an async context manager (no coroutine)
            begin_ctx = AsyncMock()
            begin_conn = AsyncMock()
            begin_conn.execute = AsyncMock()
            begin_ctx.__aenter__.return_value = begin_conn
            begin_ctx.__aexit__.return_value = AsyncMock()

            mock_engine.begin = MagicMock(return_value=begin_ctx)
            mock_create.return_value = mock_engine

            # Test creation
            await create_secure_async_engine(
                "https://test.supabase.co",
                pool_size=20,
                echo=True,
            )

            # Verify Supabase conversion
            mock_converter.return_value.supabase_to_postgres.assert_called_once()

            # Verify engine configuration
            mock_create.assert_called_once()
            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["pool_size"] == 20
            assert call_kwargs["echo"] is True
            assert call_kwargs["pool_pre_ping"] is True
            assert call_kwargs["pool_recycle"] == 3600
            assert call_kwargs["pool_timeout"] == 30

    @pytest.mark.asyncio
    async def test_create_secure_async_engine_with_invalid_url(self):
        """Test engine creation with invalid URL type."""
        with patch(
            "tripsage_core.database.connection.DatabaseURLDetector"
        ) as mock_detector:
            mock_detector.return_value.detect_url_type.return_value = {
                "type": "unknown"
            }

            with pytest.raises(DatabaseURLParsingError) as exc_info:
                await create_secure_async_engine("ftp://invalid.url")

            assert "Unsupported database URL type" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_secure_async_engine_validation_failure(
        self, mock_credentials
    ):
        """Test engine creation fails on validation."""
        with (
            patch(
                "tripsage_core.database.connection.DatabaseURLDetector"
            ) as mock_detector,
            patch(
                "tripsage_core.database.connection.create_async_engine"
            ) as mock_create,
        ):
            # Setup mocks
            mock_detector.return_value.detect_url_type.return_value = {
                "type": "postgresql"
            }

            mock_engine = AsyncMock()
            # Make validation fail
            mock_engine.begin.side_effect = Exception("Connection failed")
            mock_create.return_value = mock_engine

            with pytest.raises(DatabaseValidationError) as exc_info:
                await create_secure_async_engine("postgresql://user:pass@host/db")

            assert "Failed to validate engine connection" in str(exc_info.value)
            mock_engine.dispose.assert_called_once()

    def test_get_engine_sync_context(self, mock_settings):
        """Test get_engine in synchronous context."""
        with (
            patch(
                "tripsage_core.database.connection.get_settings",
                return_value=mock_settings,
            ),
            patch("tripsage_core.database.connection.asyncio.run") as mock_run,
            patch("tripsage_core.database.connection.create_secure_async_engine"),
        ):
            mock_engine = MagicMock()
            mock_run.return_value = mock_engine

            # Clear any cached engine
            import tripsage_core.database.connection as conn_module

            conn_module._engine = None

            engine = get_engine()

            assert engine == mock_engine
            mock_run.assert_called_once()

    def test_get_session_factory(self, mock_settings):
        """Test session factory creation."""
        with (
            patch("tripsage_core.database.connection.get_engine") as mock_get_engine,
            patch("tripsage_core.database.connection.async_sessionmaker") as mock_maker,
        ):
            mock_engine = MagicMock()
            mock_get_engine.return_value = mock_engine

            mock_factory = MagicMock()
            mock_maker.return_value = mock_factory

            # Clear cached factory
            import tripsage_core.database.connection as conn_module

            conn_module._session_factory = None

            factory = get_session_factory()

            assert factory == mock_factory
            mock_maker.assert_called_once_with(
                mock_engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False,
                autocommit=False,
            )

    @pytest.mark.asyncio
    async def test_get_database_session_context(self):
        """Test database session context manager."""
        with patch(
            "tripsage_core.database.connection.get_session_factory"
        ) as mock_factory:
            # Setup mock session
            mock_session = AsyncMock()
            mock_session.rollback = AsyncMock()
            mock_session.close = AsyncMock()

            # Setup factory context manager
            mock_session_ctx = AsyncMock()
            mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

            mock_factory.return_value.return_value = mock_session_ctx

            # Test normal operation
            async with get_database_session() as session:
                assert session == mock_session

            mock_session.close.assert_called_once()
            mock_session.rollback.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_database_session_with_error(self):
        """Test database session rollback on error."""
        with patch(
            "tripsage_core.database.connection.get_session_factory"
        ) as mock_factory:
            # Setup mock session
            mock_session = AsyncMock()
            mock_session.rollback = AsyncMock()
            mock_session.close = AsyncMock()

            # Setup factory context manager
            mock_session_ctx = AsyncMock()
            mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

            mock_factory.return_value.return_value = mock_session_ctx

            # Test with error
            with pytest.raises(RuntimeError):
                async with get_database_session():
                    raise RuntimeError("Test error")

            mock_session.rollback.assert_called_once()
            mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_test_connection_success(self):
        """Test connection validation success."""
        with patch(
            "tripsage_core.database.connection.get_database_session"
        ) as mock_session_ctx:
            # Setup mock session
            mock_session = AsyncMock()

            # Mock query results
            mock_scalar_result = MagicMock()
            mock_scalar_result.scalar.return_value = 1

            mock_info_result = MagicMock()
            mock_info_result.one.return_value = MagicMock(
                database="testdb",
                user="testuser",
                version="PostgreSQL 14.5",
                is_replica=False,
            )

            mock_ext_result = MagicMock()
            mock_ext_result.__iter__ = MagicMock(
                return_value=iter(
                    [
                        MagicMock(extname="vector", extversion="0.4.0"),
                        MagicMock(extname="uuid-ossp", extversion="1.1"),
                    ]
                )
            )

            mock_session.execute = AsyncMock(
                side_effect=[mock_scalar_result, mock_info_result, mock_ext_result]
            )

            # Setup context manager
            mock_session_ctx.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_session_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await test_connection()

            assert result is True
            assert mock_session.execute.call_count == 3

    @pytest.mark.asyncio
    async def test_test_connection_failure(self):
        """Test connection validation failure."""
        with patch(
            "tripsage_core.database.connection.get_database_session"
        ) as mock_session_ctx:
            # Make session creation fail
            mock_session_ctx.side_effect = Exception("Connection failed")

            result = await test_connection()

            assert result is False

    @pytest.mark.asyncio
    async def test_close_connections(self):
        """Test closing all connections."""
        # Setup global state
        import tripsage_core.database.connection as conn_module

        mock_engine = AsyncMock()
        mock_engine.dispose = AsyncMock()
        conn_module._engine = mock_engine
        conn_module._session_factory = MagicMock()
        conn_module._connection_manager = MagicMock()

        await close_connections()

        mock_engine.dispose.assert_called_once()
        assert conn_module._engine is None
        assert conn_module._session_factory is None
        assert conn_module._connection_manager is None

    @pytest.mark.asyncio
    async def test_get_engine_for_testing(self, mock_settings):
        """Test creating test engine with NullPool."""
        with (
            patch(
                "tripsage_core.database.connection.get_settings",
                return_value=mock_settings,
            ),
            patch(
                "tripsage_core.database.connection.create_secure_async_engine"
            ) as mock_create,
        ):
            mock_engine = AsyncMock()
            mock_engine.dispose = AsyncMock()
            mock_create.return_value = mock_engine

            test_url = "postgresql://test:test@localhost/test"

            async with get_engine_for_testing(test_url) as engine:
                assert engine == mock_engine

            # Verify NullPool was used
            mock_create.assert_called_once_with(
                test_url,
                poolclass=NullPool,
                echo=True,
            )

            # Verify cleanup
            mock_engine.dispose.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_engine_for_testing_with_queue_pool(self, mock_settings):
        """Test creating test engine with QueuePool."""
        with (
            patch(
                "tripsage_core.database.connection.get_settings",
                return_value=mock_settings,
            ),
            patch(
                "tripsage_core.database.connection.create_secure_async_engine"
            ) as mock_create,
        ):
            mock_engine = AsyncMock()
            mock_engine.dispose = AsyncMock()
            mock_create.return_value = mock_engine

            async with get_engine_for_testing(use_null_pool=False) as engine:
                assert engine == mock_engine

            # Verify QueuePool was used
            mock_create.assert_called_once()
            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["poolclass"] == QueuePool
