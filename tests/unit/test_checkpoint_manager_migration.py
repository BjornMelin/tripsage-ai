"""Unit tests for checkpoint manager migration to secure utilities."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tripsage_core.utils.connection_utils import DatabaseURLParsingError


class TestCheckpointManagerMigration:
    """Test checkpoint manager secure URL handling."""

    @pytest.fixture
    def mock_settings(self):
        """Mock settings for testing."""
        settings = MagicMock()
        settings.database_url = "https://test-project.supabase.co"
        settings.database_service_key.get_secret_value.return_value = "test-service-key"
        return settings

    @pytest.fixture
    def mock_converter(self):
        """Mock URL converter."""
        converter = MagicMock()
        converter.supabase_to_postgres.return_value = "postgresql://postgres:test-key@test-project.supabase.co:5432/postgres?sslmode=require"
        return converter

    @pytest.fixture
    def mock_manager(self):
        """Mock secure connection manager."""
        manager = MagicMock()
        manager.parse_and_validate_url = AsyncMock()
        return manager

    def test_checkpoint_manager_imports(self):
        """Test checkpoint manager can be imported with secure utilities."""
        from tripsage.orchestration.checkpoint_manager import (
            CheckpointConfig,
            SupabaseCheckpointManager,
            get_async_checkpointer,
            get_checkpoint_manager,
            get_sync_checkpointer,
        )

        # Verify imports succeed
        assert SupabaseCheckpointManager is not None
        assert CheckpointConfig is not None
        assert callable(get_checkpoint_manager)
        assert callable(get_async_checkpointer)
        assert callable(get_sync_checkpointer)

    def test_checkpoint_manager_build_connection_string(
        self, mock_settings, mock_converter, mock_manager
    ):
        """Test building connection string with secure converter."""
        with patch(
            "tripsage.orchestration.checkpoint_manager.get_settings",
            return_value=mock_settings,
        ):
            with patch(
                "tripsage.orchestration.checkpoint_manager.DatabaseURLConverter",
                return_value=mock_converter,
            ):
                with patch(
                    "tripsage.orchestration.checkpoint_manager.SecureDatabaseConnectionManager",
                    return_value=mock_manager,
                ):
                    with patch(
                        "tripsage.orchestration.checkpoint_manager.asyncio.get_running_loop",
                        side_effect=RuntimeError,
                    ):
                        with patch(
                            "tripsage.orchestration.checkpoint_manager.asyncio.run"
                        ) as mock_run:
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

                            # Verify connection string
                            assert conn_string.startswith("postgresql://")
                            assert "sslmode=require" in conn_string
                            assert "test-project.supabase.co" in conn_string

                            # Verify validation was attempted
                            mock_run.assert_called_once()

    def test_checkpoint_manager_build_connection_string_async_context(
        self, mock_settings, mock_converter, mock_manager
    ):
        """Test building connection string in async context."""
        with patch(
            "tripsage.orchestration.checkpoint_manager.get_settings",
            return_value=mock_settings,
        ):
            with patch(
                "tripsage.orchestration.checkpoint_manager.DatabaseURLConverter",
                return_value=mock_converter,
            ):
                with patch(
                    "tripsage.orchestration.checkpoint_manager.SecureDatabaseConnectionManager",
                    return_value=mock_manager,
                ):
                    # Mock async context
                    mock_loop = MagicMock()
                    mock_task = MagicMock()
                    mock_loop.create_task.return_value = mock_task

                    with patch(
                        "tripsage.orchestration.checkpoint_manager.asyncio.get_running_loop",
                        return_value=mock_loop,
                    ):
                        from tripsage.orchestration.checkpoint_manager import (
                            SupabaseCheckpointManager,
                        )

                        manager = SupabaseCheckpointManager()
                        conn_string = manager._build_connection_string()

                        # Verify task was created for validation
                        mock_loop.create_task.assert_called_once()

                        # Verify connection string
                        assert "postgresql://" in conn_string
                        assert "sslmode=require" in conn_string

    def test_checkpoint_manager_connection_string_caching(
        self, mock_settings, mock_converter
    ):
        """Test connection string is cached after first build."""
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
                ):
                    with patch("tripsage.orchestration.checkpoint_manager.asyncio.run"):
                        from tripsage.orchestration.checkpoint_manager import (
                            SupabaseCheckpointManager,
                        )

                        manager = SupabaseCheckpointManager()

                        # First call
                        conn_string1 = manager._build_connection_string()

                        # Second call
                        conn_string2 = manager._build_connection_string()

                        # Should be the same instance
                        assert conn_string1 is conn_string2

                        # Converter should only be called once
                        mock_converter.supabase_to_postgres.assert_called_once()

    def test_checkpoint_manager_error_handling(self, mock_settings, mock_converter):
        """Test error handling in connection string building."""
        with (
            patch(
                "tripsage.orchestration.checkpoint_manager.get_settings",
                return_value=mock_settings,
            ),
            patch(
                "tripsage.orchestration.checkpoint_manager.DatabaseURLConverter",
                return_value=mock_converter,
            ),
        ):
            # Make conversion fail
            mock_converter.supabase_to_postgres.side_effect = Exception(
                "Conversion failed"
            )

            from tripsage.orchestration.checkpoint_manager import (
                SupabaseCheckpointManager,
            )

            manager = SupabaseCheckpointManager()

            with pytest.raises(DatabaseURLParsingError) as exc_info:
                manager._build_connection_string()

            assert "Could not create secure checkpoint connection" in str(
                exc_info.value
            )
            assert "Conversion failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_checkpoint_manager_async_checkpointer(
        self, mock_settings, mock_converter
    ):
        """Test async checkpointer initialization."""
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
                ):
                    with patch("tripsage.orchestration.checkpoint_manager.asyncio.run"):
                        from tripsage.orchestration.checkpoint_manager import (
                            POSTGRES_AVAILABLE,
                            SupabaseCheckpointManager,
                        )

                        if not POSTGRES_AVAILABLE:
                            pytest.skip(
                                "PostgreSQL checkpoint dependencies not available"
                            )

                        # Mock pool creation
                        with patch(
                            "tripsage.orchestration.checkpoint_manager.AsyncConnectionPool"
                        ) as mock_pool:
                            manager = SupabaseCheckpointManager()

                            # Mock the checkpointer
                            with patch(
                                "tripsage.orchestration.checkpoint_manager.AsyncPostgresSaver"
                            ) as mock_saver:
                                mock_checkpointer = MagicMock()
                                mock_checkpointer.setup = AsyncMock()
                                mock_saver.return_value = mock_checkpointer

                                await manager.get_async_checkpointer()

                                # Verify pool was created with secure connection string
                                mock_pool.assert_called_once()
                                pool_config = mock_pool.call_args[1]
                                assert "postgresql://" in pool_config["conninfo"]
                                assert "sslmode=require" in pool_config["conninfo"]

                                # Verify checkpointer was created
                                mock_saver.assert_called_once()

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

    def test_global_checkpoint_manager_singleton(self):
        """Test global checkpoint manager is a singleton."""
        from tripsage.orchestration.checkpoint_manager import get_checkpoint_manager

        manager1 = get_checkpoint_manager()
        manager2 = get_checkpoint_manager()

        assert manager1 is manager2

    @pytest.mark.asyncio
    async def test_checkpoint_manager_cleanup(self, mock_settings, mock_converter):
        """Test checkpoint manager cleanup."""
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
                ):
                    with patch("tripsage.orchestration.checkpoint_manager.asyncio.run"):
                        from tripsage.orchestration.checkpoint_manager import (
                            SupabaseCheckpointManager,
                        )

                        manager = SupabaseCheckpointManager()

                        # Mock pools
                        manager._async_connection_pool = AsyncMock()
                        manager._connection_pool = MagicMock()
                        manager._connection_pool.close = MagicMock()

                        await manager.close()

                        # Verify pools were closed
                        manager._async_connection_pool.close.assert_called_once()
                        manager._connection_pool.close.assert_called_once()
