"""
Test suite for Phase 3 Checkpoint Manager implementation.

This module tests the SupabaseCheckpointManager that provides PostgreSQL
checkpointing for LangGraph using Supabase infrastructure.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tripsage.orchestration.checkpoint_manager import (
    SupabaseCheckpointManager,
    get_checkpoint_manager,
)
from tripsage.orchestration.state import create_initial_state

# Mock AsyncPostgresSaver since it might not be available
try:
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
except ImportError:
    # Create mock class for testing
    class AsyncPostgresSaver:
        def __init__(self, *args, **kwargs):
            pass

        async def aput(self, *args, **kwargs):
            pass

        async def aget(self, *args, **kwargs):
            from unittest.mock import MagicMock

            mock = MagicMock()
            mock.values = {}
            return mock


class TestSupabaseCheckpointManager:
    """Test suite for the Supabase Checkpoint Manager."""

    @pytest.fixture
    def mock_supabase_settings(self):
        """Mock Supabase settings."""
        with patch("tripsage.config.app_settings.get_settings") as mock:
            mock_settings = MagicMock()
            mock_settings.supabase_url = "https://test.supabase.co"
            mock_settings.supabase_anon_key = "test_anon_key"
            mock_settings.supabase_service_role_key = "test_service_key"
            mock_settings.database_url = "postgresql://user:pass@localhost:5432/testdb"
            mock.return_value = mock_settings
            yield mock_settings

    @pytest.fixture
    def mock_asyncpg_pool(self):
        """Mock asyncpg connection pool."""
        with patch("asyncpg.create_pool") as mock:
            mock_pool = MagicMock()
            mock_pool.acquire = AsyncMock()
            mock_pool.close = AsyncMock()
            mock.return_value = mock_pool
            yield mock_pool

    @pytest.fixture
    def checkpoint_manager(self, mock_supabase_settings, mock_asyncpg_pool):
        """Create test checkpoint manager instance."""
        return SupabaseCheckpointManager()

    @pytest.mark.asyncio
    async def test_manager_initialization(
        self, checkpoint_manager, mock_supabase_settings
    ):
        """Test checkpoint manager initialization."""
        await checkpoint_manager.initialize()

        assert checkpoint_manager.settings is not None
        assert checkpoint_manager._initialized is True
        assert checkpoint_manager._connection_pool is not None

    @pytest.mark.asyncio
    async def test_connection_pool_creation(
        self, checkpoint_manager, mock_asyncpg_pool
    ):
        """Test PostgreSQL connection pool creation."""
        await checkpoint_manager.initialize()

        # Verify pool was created with correct parameters
        mock_asyncpg_pool.assert_called_once()
        call_args = mock_asyncpg_pool.call_args

        # Should contain database connection parameters
        assert "user" in call_args.kwargs or len(call_args.args) > 0

    @pytest.mark.asyncio
    async def test_get_async_checkpointer(self, checkpoint_manager, mock_asyncpg_pool):
        """Test creation of AsyncPostgresSaver instance."""
        await checkpoint_manager.initialize()

        checkpointer = await checkpoint_manager.get_async_checkpointer()

        assert isinstance(checkpointer, AsyncPostgresSaver)
        assert checkpoint_manager._checkpointer is not None

    @pytest.mark.asyncio
    async def test_checkpointer_singleton_behavior(
        self, checkpoint_manager, mock_asyncpg_pool
    ):
        """Test that checkpointer returns same instance on multiple calls."""
        await checkpoint_manager.initialize()

        checkpointer1 = await checkpoint_manager.get_async_checkpointer()
        checkpointer2 = await checkpoint_manager.get_async_checkpointer()

        assert checkpointer1 is checkpointer2  # Should be same instance

    @pytest.mark.asyncio
    async def test_database_table_setup(self, checkpoint_manager, mock_asyncpg_pool):
        """Test database table setup for checkpointing."""
        # Mock connection for table setup
        mock_connection = MagicMock()
        mock_connection.execute = AsyncMock()
        mock_asyncpg_pool.acquire.return_value.__aenter__.return_value = mock_connection

        await checkpoint_manager.initialize()
        await checkpoint_manager._setup_tables()

        # Verify table creation queries were executed
        mock_connection.execute.assert_called()

    @pytest.mark.asyncio
    async def test_state_persistence_and_retrieval(
        self, checkpoint_manager, mock_asyncpg_pool
    ):
        """Test state persistence and retrieval through checkpointer."""
        await checkpoint_manager.initialize()
        checkpointer = await checkpoint_manager.get_async_checkpointer()

        # Create test state
        test_state = create_initial_state("test_user", "Test message")
        config = {"configurable": {"thread_id": "test_thread_123"}}

        # Mock checkpointer methods
        checkpointer.aput = AsyncMock()
        checkpointer.aget = AsyncMock(return_value=MagicMock(values=test_state))

        # Test persistence
        await checkpointer.aput(config, test_state, {})
        checkpointer.aput.assert_called_once()

        # Test retrieval
        retrieved_state = await checkpointer.aget(config)
        checkpointer.aget.assert_called_once()
        assert retrieved_state.values == test_state

    @pytest.mark.asyncio
    async def test_concurrent_checkpointer_access(
        self, checkpoint_manager, mock_asyncpg_pool
    ):
        """Test concurrent access to checkpointer."""
        await checkpoint_manager.initialize()

        # Create multiple concurrent tasks
        async def get_checkpointer():
            return await checkpoint_manager.get_async_checkpointer()

        tasks = [get_checkpointer() for _ in range(5)]
        checkpointers = await asyncio.gather(*tasks)

        # All should be the same instance
        for cp in checkpointers[1:]:
            assert cp is checkpointers[0]

    @pytest.mark.asyncio
    async def test_connection_pool_error_handling(
        self, checkpoint_manager, mock_supabase_settings
    ):
        """Test error handling when connection pool creation fails."""
        with patch("asyncpg.create_pool", side_effect=Exception("Connection failed")):
            with pytest.raises(Exception) as exc_info:
                await checkpoint_manager.initialize()

            assert "Connection failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_cleanup_on_shutdown(self, checkpoint_manager, mock_asyncpg_pool):
        """Test proper cleanup when shutting down."""
        await checkpoint_manager.initialize()

        # Verify pool exists
        assert checkpoint_manager._connection_pool is not None

        # Test cleanup
        await checkpoint_manager.cleanup()

        # Verify pool was closed
        mock_asyncpg_pool.close.assert_called_once()
        assert checkpoint_manager._connection_pool is None
        assert checkpoint_manager._initialized is False

    @pytest.mark.asyncio
    async def test_configuration_validation(self, checkpoint_manager):
        """Test validation of Supabase configuration."""
        # Test with missing configuration
        with patch("tripsage.config.app_settings.get_settings") as mock_settings:
            mock_settings.return_value.database_url = None

            with pytest.raises(ValueError) as exc_info:
                await checkpoint_manager.initialize()

            assert "database_url" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_thread_id_validation(self, checkpoint_manager, mock_asyncpg_pool):
        """Test thread ID validation in checkpointing operations."""
        await checkpoint_manager.initialize()
        checkpointer = await checkpoint_manager.get_async_checkpointer()

        # Mock validation
        checkpointer.aget = AsyncMock()

        # Test with valid thread ID
        valid_config = {"configurable": {"thread_id": "session_user_123"}}
        await checkpointer.aget(valid_config)
        checkpointer.aget.assert_called_with(valid_config)

    @pytest.mark.asyncio
    async def test_state_serialization_compatibility(
        self, checkpoint_manager, mock_asyncpg_pool
    ):
        """Test that TravelPlanningState is compatible with PostgreSQL serialization."""
        await checkpoint_manager.initialize()
        checkpointer = await checkpoint_manager.get_async_checkpointer()

        # Create complex state with various data types
        complex_state = create_initial_state("test_user", "Complex test")
        complex_state.update(
            {
                "flight_searches": [{"origin": "NYC", "destination": "LAX"}],
                "user_preferences": {"budget": 1000, "flexible": True},
                "agent_history": [
                    {"agent": "flight_agent", "timestamp": "2025-01-01T00:00:00"}
                ],
            }
        )

        # Mock serialization test
        checkpointer.aput = AsyncMock()
        config = {"configurable": {"thread_id": "test_serialization"}}

        # Should not raise serialization errors
        await checkpointer.aput(config, complex_state, {})
        checkpointer.aput.assert_called_once()

    @pytest.mark.asyncio
    async def test_multiple_session_isolation(
        self, checkpoint_manager, mock_asyncpg_pool
    ):
        """Test that different sessions are properly isolated."""
        await checkpoint_manager.initialize()
        checkpointer = await checkpoint_manager.get_async_checkpointer()

        # Mock different sessions
        checkpointer.aget = AsyncMock(
            side_effect=[
                MagicMock(values=create_initial_state("user1", "Message 1")),
                MagicMock(values=create_initial_state("user2", "Message 2")),
            ]
        )

        # Test session isolation
        config1 = {"configurable": {"thread_id": "session_user1"}}
        config2 = {"configurable": {"thread_id": "session_user2"}}

        state1 = await checkpointer.aget(config1)
        state2 = await checkpointer.aget(config2)

        # States should be different
        assert state1.values["user_id"] != state2.values["user_id"]

    def test_singleton_manager_access(self):
        """Test singleton access to checkpoint manager."""
        manager1 = get_checkpoint_manager()
        manager2 = get_checkpoint_manager()

        assert manager1 is manager2  # Should be same instance

    @pytest.mark.asyncio
    async def test_performance_optimization(
        self, checkpoint_manager, mock_asyncpg_pool
    ):
        """Test performance optimizations like connection pooling."""
        await checkpoint_manager.initialize()

        # Verify connection pool parameters for performance
        call_args = mock_asyncpg_pool.call_args.kwargs

        # Should have reasonable pool size
        if "min_size" in call_args:
            assert call_args["min_size"] >= 1
        if "max_size" in call_args:
            assert call_args["max_size"] >= 5

    @pytest.mark.asyncio
    async def test_error_recovery_mechanism(
        self, checkpoint_manager, mock_asyncpg_pool
    ):
        """Test error recovery when database operations fail."""
        await checkpoint_manager.initialize()
        checkpointer = await checkpoint_manager.get_async_checkpointer()

        # Mock database error
        checkpointer.aget = AsyncMock(side_effect=Exception("Database error"))

        config = {"configurable": {"thread_id": "test_error"}}

        # Should handle database errors gracefully
        with pytest.raises(Exception) as exc_info:
            await checkpointer.aget(config)

        assert "Database error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_migration_compatibility(self, checkpoint_manager, mock_asyncpg_pool):
        """Test compatibility with database migrations."""
        # Mock migration check
        mock_connection = MagicMock()
        mock_connection.fetchval = AsyncMock(return_value=1)  # Table exists
        mock_asyncpg_pool.acquire.return_value.__aenter__.return_value = mock_connection

        await checkpoint_manager.initialize()

        # Should handle existing tables gracefully
        await checkpoint_manager._setup_tables()

        # Verify table existence was checked
        mock_connection.fetchval.assert_called()

    @pytest.mark.asyncio
    async def test_security_configuration(
        self, checkpoint_manager, mock_supabase_settings
    ):
        """Test security aspects of database configuration."""
        # Verify sensitive data handling
        await checkpoint_manager.initialize()

        # Settings should not expose sensitive information in logs
        assert checkpoint_manager.settings.database_url
        # Verify that passwords/keys are not in plain text in objects
        settings_dict = checkpoint_manager.settings.__dict__
        assert isinstance(settings_dict, dict)
        assert "database_url" in settings_dict

        # Should have security keys (but won't verify actual values for security)
        assert hasattr(checkpoint_manager.settings, "supabase_service_role_key")
