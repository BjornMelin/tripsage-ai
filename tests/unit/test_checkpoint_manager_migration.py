"""Unit tests for final checkpoint manager implementation."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tripsage_core.utils.connection_utils import DatabaseURLParsingError


class TestCheckpointManager:
    """Test final checkpointer wiring and URL building."""

    @pytest.fixture
    def mock_settings(self):
        """Mock project settings with Supabase URL."""
        settings = MagicMock()
        settings.database_url = "https://test-project.supabase.co"
        settings.database_service_key.get_secret_value.return_value = "test-service-key"
        return settings

    def test_imports(self):
        """Checkpoint manager exports should be importable."""
        from tripsage.orchestration.checkpoint_manager import SupabaseCheckpointManager

        assert SupabaseCheckpointManager is not None

    def test_build_connection_string_supabase(self, mock_settings):
        """Test building connection string from Supabase URL."""
        with (
            patch(
                "tripsage.orchestration.checkpoint_manager.get_settings",
                return_value=mock_settings,
            ),
            patch(
                "tripsage.orchestration.checkpoint_manager.DatabaseURLDetector"
            ) as mock_detector,
            patch(
                "tripsage.orchestration.checkpoint_manager.DatabaseURLConverter"
            ) as mock_converter,
            patch(
                "tripsage.orchestration.checkpoint_manager.DatabaseURLParser"
            ) as mock_parser,
        ):
            mock_detector.return_value.detect_url_type.return_value = {
                "type": "supabase",
            }
            mock_converter.return_value.supabase_to_postgres.return_value = "postgresql://postgres:test-service-key@test-project.db.supabase.co:5432/postgres?sslmode=require"
            mock_parser.return_value.parse_url.return_value = MagicMock()

            from tripsage.orchestration.checkpoint_manager import (
                SupabaseCheckpointManager,
            )

            mgr = SupabaseCheckpointManager()
            conn = mgr._build_connection_string()

            assert conn.startswith("postgresql://")
            assert "sslmode=require" in conn
            mock_converter.return_value.supabase_to_postgres.assert_called_once()
            mock_parser.return_value.parse_url.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_checkpointer_uses_conn_string(self, mock_settings):
        """Test that async checkpointer is created with correct connection string."""
        with (
            patch(
                "tripsage.orchestration.checkpoint_manager.get_settings",
                return_value=mock_settings,
            ),
            patch(
                "tripsage.orchestration.checkpoint_manager.POSTGRES_AVAILABLE",
                True,
            ),
            patch(
                "tripsage.orchestration.checkpoint_manager.DatabaseURLDetector"
            ) as mock_detector,
            patch(
                "tripsage.orchestration.checkpoint_manager.DatabaseURLConverter"
            ) as mock_converter,
            patch(
                "tripsage.orchestration.checkpoint_manager.DatabaseURLParser"
            ) as mock_parser,
            patch(
                "tripsage.orchestration.checkpoint_manager.AsyncPostgresSaver"
            ) as mock_async_saver,
        ):
            mock_detector.return_value.detect_url_type.return_value = {
                "type": "supabase",
            }
            mock_converter.return_value.supabase_to_postgres.return_value = "postgresql://postgres:test-service-key@test-project.db.supabase.co:5432/postgres?sslmode=require"
            mock_parser.return_value.parse_url.return_value = MagicMock()

            mock_instance = AsyncMock()
            mock_async_saver.from_conn_string = AsyncMock(return_value=mock_instance)

            from tripsage.orchestration.checkpoint_manager import (
                SupabaseCheckpointManager,
            )

            mgr = SupabaseCheckpointManager()
            cp = await mgr.get_async_checkpointer()

            assert cp == mock_instance
            mock_async_saver.from_conn_string.assert_called_once()
            mock_instance.setup.assert_awaited()

    def test_error_on_unsupported_url(self, mock_settings):
        """Test error raised on unsupported database URL type."""
        with patch(
            "tripsage.orchestration.checkpoint_manager.DatabaseURLDetector"
        ) as mock_detector:
            mock_detector.return_value.detect_url_type.return_value = {
                "type": "unknown",
            }
            from tripsage.orchestration.checkpoint_manager import (
                SupabaseCheckpointManager,
            )

            mgr = SupabaseCheckpointManager()
            with pytest.raises(DatabaseURLParsingError):
                mgr._build_connection_string()

    def test_checkpoint_config(self):
        """Test CheckpointConfig class."""
        from tripsage.orchestration.checkpoint_manager import CheckpointConfig

        # Test default values
        config = CheckpointConfig()
        assert config.cleanup_interval_hours == 24
        assert config.max_checkpoint_age_days == 30
        assert config.pool_size == 20
        assert config.enable_stats is True

        # Test custom values
        config = CheckpointConfig(
            cleanup_interval_hours=12,
            max_checkpoint_age_days=7,
            pool_size=50,
            enable_stats=False,
        )
        assert config.cleanup_interval_hours == 12
        assert config.max_checkpoint_age_days == 7
        assert config.pool_size == 50
        assert config.enable_stats is False

    def test_service_registry_checkpoint_singleton(self):
        """ServiceRegistry should manage checkpoint manager lifecycle."""
        from tripsage.agents.service_registry import ServiceRegistry

        registry = ServiceRegistry()
        manager1 = registry.get_checkpoint_manager()
        manager2 = registry.get_checkpoint_manager()

        assert manager1 is manager2

    def test_service_registry_memory_bridge_singleton(self):
        """Verify ServiceRegistry memoizes the session memory bridge."""
        from tripsage.agents.service_registry import ServiceRegistry

        registry = ServiceRegistry(memory_bridge=None)
        bridge1 = registry.get_memory_bridge()
        bridge2 = registry.get_memory_bridge()

        assert bridge1 is bridge2

    @pytest.mark.asyncio
    async def test_service_registry_mcp_bridge_singleton(self):
        """Verify ServiceRegistry memoizes the MCP bridge."""
        from tripsage.agents.service_registry import ServiceRegistry

        registry = ServiceRegistry()
        bridge1 = await registry.get_mcp_bridge()
        bridge2 = await registry.get_mcp_bridge()

        assert bridge1 is bridge2
