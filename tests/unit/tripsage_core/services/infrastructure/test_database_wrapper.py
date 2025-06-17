"""
Tests for database service wrapper with monitoring integration.

Tests cover feature flag-based monitoring, graceful degradation,
and transparent pass-through of database operations.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from tripsage_core.config import Settings
from tripsage_core.monitoring.database_metrics import DatabaseMetrics
from tripsage_core.services.infrastructure.database_monitor import (
    ConsolidatedDatabaseMonitor,
)
from tripsage_core.services.infrastructure.database_wrapper import (
    DatabaseServiceWrapper,
    close_database_wrapper,
    get_database_wrapper,
)


class TestDatabaseServiceWrapper:
    """Test suite for DatabaseServiceWrapper class."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create settings with monitoring enabled
        self.settings_enabled = Settings(
            enable_database_monitoring=True,
            enable_prometheus_metrics=True,
            enable_security_monitoring=True,
            enable_metrics_server=False,
        )

        # Create settings with monitoring disabled
        self.settings_disabled = Settings(
            enable_database_monitoring=False,
            enable_prometheus_metrics=False,
            enable_security_monitoring=False,
        )

    @patch("tripsage_core.services.infrastructure.database_wrapper.DatabaseService")
    @patch(
        "tripsage_core.services.infrastructure.database_wrapper.get_database_metrics"
    )
    @patch(
        "tripsage_core.services.infrastructure.database_wrapper.ConsolidatedDatabaseMonitor"
    )
    def test_initialization_with_monitoring_enabled(
        self, mock_monitor_class, mock_get_metrics, mock_db_service_class
    ):
        """Test wrapper initialization with monitoring enabled."""
        mock_metrics = Mock(spec=DatabaseMetrics)
        mock_get_metrics.return_value = mock_metrics
        mock_monitor = Mock(spec=ConsolidatedDatabaseMonitor)
        mock_monitor_class.return_value = mock_monitor
        mock_db_service = Mock()
        mock_db_service_class.return_value = mock_db_service

        wrapper = DatabaseServiceWrapper(self.settings_enabled)

        assert wrapper.settings == self.settings_enabled
        assert wrapper.database_service == mock_db_service
        assert wrapper.metrics == mock_metrics
        assert wrapper.monitor == mock_monitor

        # Verify monitor was configured
        mock_monitor.configure_monitoring.assert_called_once()

    @patch("tripsage_core.services.infrastructure.database_wrapper.DatabaseService")
    def test_initialization_with_monitoring_disabled(self, mock_db_service_class):
        """Test wrapper initialization with monitoring disabled."""
        mock_db_service = Mock()
        mock_db_service_class.return_value = mock_db_service

        wrapper = DatabaseServiceWrapper(self.settings_disabled)

        assert wrapper.settings == self.settings_disabled
        assert wrapper.database_service == mock_db_service
        assert wrapper.metrics is None
        assert wrapper.monitor is None

    @patch("tripsage_core.services.infrastructure.database_wrapper.DatabaseService")
    @patch(
        "tripsage_core.services.infrastructure.database_wrapper.get_database_metrics"
    )
    def test_initialization_with_metrics_error(
        self, mock_get_metrics, mock_db_service_class
    ):
        """Test wrapper initialization handles metrics initialization errors."""
        mock_get_metrics.side_effect = Exception("Metrics initialization failed")
        mock_db_service = Mock()
        mock_db_service_class.return_value = mock_db_service

        # Should not raise exception, just continue without monitoring
        wrapper = DatabaseServiceWrapper(self.settings_enabled)

        assert wrapper.metrics is None
        assert wrapper.monitor is None

    def test_property_delegation(self):
        """Test that properties are delegated to database service."""
        with patch(
            "tripsage_core.services.infrastructure.database_wrapper.DatabaseService"
        ) as mock_db_service_class:
            mock_db_service = Mock()
            mock_db_service.is_connected = True
            mock_db_service.client = "mock_client"
            mock_db_service_class.return_value = mock_db_service

            wrapper = DatabaseServiceWrapper(self.settings_disabled)

            assert wrapper.is_connected
            assert wrapper.client == "mock_client"

    @pytest.mark.asyncio
    async def test_connect_with_monitoring(self):
        """Test connection with monitoring enabled."""
        with (
            patch(
                "tripsage_core.services.infrastructure.database_wrapper.DatabaseService"
            ) as mock_db_service_class,
            patch(
                "tripsage_core.services.infrastructure.database_wrapper.get_database_metrics"
            ) as mock_get_metrics,
            patch(
                "tripsage_core.services.infrastructure.database_wrapper.ConsolidatedDatabaseMonitor"
            ) as mock_monitor_class,
        ):
            mock_db_service = Mock()
            mock_db_service.connect = AsyncMock()
            mock_db_service_class.return_value = mock_db_service

            mock_metrics = Mock()
            mock_metrics.record_connection_attempt = Mock()
            mock_metrics.start_metrics_server = Mock()
            mock_get_metrics.return_value = mock_metrics

            mock_monitor = Mock()
            mock_monitor.start_monitoring = AsyncMock()
            mock_monitor.configure_monitoring = Mock()
            mock_monitor_class.return_value = mock_monitor

            wrapper = DatabaseServiceWrapper(self.settings_enabled)
            await wrapper.connect()

            # Verify database service connect was called
            mock_db_service.connect.assert_called_once()

            # Verify monitoring was started
            mock_monitor.start_monitoring.assert_called_once()

            # Verify metrics recorded connection attempt
            mock_metrics.record_connection_attempt.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_with_metrics_server(self):
        """Test connection with metrics server enabled."""
        settings_with_server = Settings(
            enable_database_monitoring=True,
            enable_prometheus_metrics=True,
            enable_metrics_server=True,
            metrics_server_port=8001,
        )

        with (
            patch(
                "tripsage_core.services.infrastructure.database_wrapper.DatabaseService"
            ) as mock_db_service_class,
            patch(
                "tripsage_core.services.infrastructure.database_wrapper.get_database_metrics"
            ) as mock_get_metrics,
        ):
            mock_db_service = Mock()
            mock_db_service.connect = AsyncMock()
            mock_db_service_class.return_value = mock_db_service

            mock_metrics = Mock()
            mock_metrics.record_connection_attempt = Mock()
            mock_metrics.start_metrics_server = Mock()
            mock_get_metrics.return_value = mock_metrics

            wrapper = DatabaseServiceWrapper(settings_with_server)
            await wrapper.connect()

            # Verify metrics server was started
            mock_metrics.start_metrics_server.assert_called_once_with(8001)

    @pytest.mark.asyncio
    async def test_connect_failure_recorded(self):
        """Test that connection failures are recorded."""
        with (
            patch(
                "tripsage_core.services.infrastructure.database_wrapper.DatabaseService"
            ) as mock_db_service_class,
            patch(
                "tripsage_core.services.infrastructure.database_wrapper.get_database_metrics"
            ) as mock_get_metrics,
            patch(
                "tripsage_core.services.infrastructure.database_wrapper.ConsolidatedDatabaseMonitor"
            ) as mock_monitor_class,
        ):
            mock_db_service = Mock()
            mock_db_service.connect = AsyncMock(
                side_effect=Exception("Connection failed")
            )
            mock_db_service_class.return_value = mock_db_service

            mock_metrics = Mock()
            mock_metrics.record_connection_attempt = Mock()
            mock_get_metrics.return_value = mock_metrics

            mock_monitor = Mock()
            mock_monitor.record_connection_failure = Mock()
            mock_monitor.configure_monitoring = Mock()
            mock_monitor_class.return_value = mock_monitor

            wrapper = DatabaseServiceWrapper(self.settings_enabled)

            with pytest.raises(Exception, match="Connection failed"):
                await wrapper.connect()

            # Verify failure was recorded
            mock_monitor.record_connection_failure.assert_called_once()
            mock_metrics.record_connection_attempt.assert_called_once()
            # Verify it was recorded as failure
            args = mock_metrics.record_connection_attempt.call_args[0]
            assert not args[1]  # success=False

    @pytest.mark.asyncio
    async def test_close_with_monitoring(self):
        """Test closing connection with monitoring."""
        with (
            patch(
                "tripsage_core.services.infrastructure.database_wrapper.DatabaseService"
            ) as mock_db_service_class,
            patch(
                "tripsage_core.services.infrastructure.database_wrapper.ConsolidatedDatabaseMonitor"
            ) as mock_monitor_class,
        ):
            mock_db_service = Mock()
            mock_db_service.close = AsyncMock()
            mock_db_service_class.return_value = mock_db_service

            mock_monitor = Mock()
            mock_monitor.stop_monitoring = AsyncMock()
            mock_monitor.configure_monitoring = Mock()
            mock_monitor_class.return_value = mock_monitor

            wrapper = DatabaseServiceWrapper(self.settings_enabled)
            await wrapper.close()

            # Verify monitoring was stopped first
            mock_monitor.stop_monitoring.assert_called_once()

            # Verify database service was closed
            mock_db_service.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_with_monitor_error(self):
        """Test closing handles monitor errors gracefully."""
        with (
            patch(
                "tripsage_core.services.infrastructure.database_wrapper.DatabaseService"
            ) as mock_db_service_class,
            patch(
                "tripsage_core.services.infrastructure.database_wrapper.ConsolidatedDatabaseMonitor"
            ) as mock_monitor_class,
        ):
            mock_db_service = Mock()
            mock_db_service.close = AsyncMock()
            mock_db_service_class.return_value = mock_db_service

            mock_monitor = Mock()
            mock_monitor.stop_monitoring = AsyncMock(
                side_effect=Exception("Monitor error")
            )
            mock_monitor.configure_monitoring = Mock()
            mock_monitor_class.return_value = mock_monitor

            wrapper = DatabaseServiceWrapper(self.settings_enabled)

            # Should not raise exception
            await wrapper.close()

            # Database service should still be closed
            mock_db_service.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_database_operations_with_metrics(self):
        """Test database operations with metrics collection."""
        with (
            patch(
                "tripsage_core.services.infrastructure.database_wrapper.DatabaseService"
            ) as mock_db_service_class,
            patch(
                "tripsage_core.services.infrastructure.database_wrapper.get_database_metrics"
            ) as mock_get_metrics,
        ):
            mock_db_service = Mock()
            mock_db_service.insert = AsyncMock(return_value=[{"id": "123"}])
            mock_db_service.select = AsyncMock(return_value=[{"id": "456"}])
            mock_db_service.update = AsyncMock(return_value=[{"id": "789"}])
            mock_db_service.delete = AsyncMock(return_value=[{"id": "999"}])
            mock_db_service.count = AsyncMock(return_value=5)
            mock_db_service_class.return_value = mock_db_service

            mock_metrics = Mock()
            mock_metrics.time_query = Mock()
            mock_metrics.time_query.return_value.__enter__ = Mock()
            mock_metrics.time_query.return_value.__exit__ = Mock()
            mock_get_metrics.return_value = mock_metrics

            wrapper = DatabaseServiceWrapper(self.settings_enabled)

            # Test operations
            await wrapper.insert("users", {"name": "test"})
            await wrapper.select("users", "*")
            await wrapper.update("users", {"name": "updated"}, {"id": "123"})
            await wrapper.delete("users", {"id": "123"})
            await wrapper.count("users")

            # Verify metrics timing was used
            assert mock_metrics.time_query.call_count == 5

    @pytest.mark.asyncio
    async def test_database_operations_without_metrics(self):
        """Test database operations without metrics collection."""
        with patch(
            "tripsage_core.services.infrastructure.database_wrapper.DatabaseService"
        ) as mock_db_service_class:
            mock_db_service = Mock()
            mock_db_service.insert = AsyncMock(return_value=[{"id": "123"}])
            mock_db_service.select = AsyncMock(return_value=[{"id": "456"}])
            mock_db_service_class.return_value = mock_db_service

            wrapper = DatabaseServiceWrapper(self.settings_disabled)

            # Test operations
            result1 = await wrapper.insert("users", {"name": "test"})
            result2 = await wrapper.select("users", "*")

            # Verify operations were called directly
            mock_db_service.insert.assert_called_once_with("users", {"name": "test"})
            mock_db_service.select.assert_called_once_with(
                "users", "*", None, None, None, None
            )

            assert result1 == [{"id": "123"}]
            assert result2 == [{"id": "456"}]

    @pytest.mark.asyncio
    async def test_transaction_with_metrics(self):
        """Test transaction context manager with metrics."""
        with (
            patch(
                "tripsage_core.services.infrastructure.database_wrapper.DatabaseService"
            ) as mock_db_service_class,
            patch(
                "tripsage_core.services.infrastructure.database_wrapper.get_database_metrics"
            ) as mock_get_metrics,
        ):
            mock_db_service = Mock()
            mock_transaction = AsyncMock()
            mock_db_service.transaction.return_value.__aenter__ = AsyncMock(
                return_value=mock_transaction
            )
            mock_db_service.transaction.return_value.__aexit__ = AsyncMock()
            mock_db_service_class.return_value = mock_db_service

            mock_metrics = Mock()
            mock_metrics.time_transaction = Mock()
            mock_metrics.time_transaction.return_value.__enter__ = Mock()
            mock_metrics.time_transaction.return_value.__exit__ = Mock()
            mock_get_metrics.return_value = mock_metrics

            wrapper = DatabaseServiceWrapper(self.settings_enabled)

            async with wrapper.transaction() as tx:
                assert tx == mock_transaction

            # Verify transaction timing was used
            mock_metrics.time_transaction.assert_called_once_with("supabase")

    def test_pass_through_methods(self):
        """Test that high-level methods are passed through correctly."""
        with patch(
            "tripsage_core.services.infrastructure.database_wrapper.DatabaseService"
        ) as mock_db_service_class:
            mock_db_service = Mock()
            mock_db_service.create_trip = AsyncMock(return_value={"id": "trip123"})
            mock_db_service.get_user = AsyncMock(return_value={"id": "user123"})
            mock_db_service.health_check = AsyncMock(return_value=True)
            mock_db_service_class.return_value = mock_db_service

            wrapper = DatabaseServiceWrapper(self.settings_disabled)

            # Test that methods exist and delegate correctly
            assert hasattr(wrapper, "create_trip")
            assert hasattr(wrapper, "get_user")
            assert hasattr(wrapper, "health_check")

    def test_monitoring_access_methods_enabled(self):
        """Test monitoring access methods when monitoring is enabled."""
        with (
            patch(
                "tripsage_core.services.infrastructure.database_wrapper.DatabaseService"
            ),
            patch(
                "tripsage_core.services.infrastructure.database_wrapper.get_database_metrics"
            ) as mock_get_metrics,
            patch(
                "tripsage_core.services.infrastructure.database_wrapper.ConsolidatedDatabaseMonitor"
            ) as mock_monitor_class,
        ):
            mock_metrics = Mock()
            mock_metrics.get_metrics_summary = Mock(return_value={"test": "data"})
            mock_get_metrics.return_value = mock_metrics

            mock_monitor = Mock()
            mock_monitor.get_monitoring_status = Mock(return_value={"status": "active"})
            mock_monitor.get_current_health = Mock(return_value="healthy")
            mock_monitor.get_security_alerts = Mock(return_value=[])
            mock_monitor.configure_monitoring = Mock()
            mock_monitor_class.return_value = mock_monitor

            wrapper = DatabaseServiceWrapper(self.settings_enabled)

            # Test monitoring access methods
            assert wrapper.get_monitoring_status() == {"status": "active"}
            assert wrapper.get_current_health() == "healthy"
            assert wrapper.get_security_alerts() == []
            assert wrapper.get_metrics_summary() == {"test": "data"}

    def test_monitoring_access_methods_disabled(self):
        """Test monitoring access methods when monitoring is disabled."""
        with patch(
            "tripsage_core.services.infrastructure.database_wrapper.DatabaseService"
        ):
            wrapper = DatabaseServiceWrapper(self.settings_disabled)

            # Test monitoring access methods return None/empty when disabled
            assert wrapper.get_monitoring_status() is None
            assert wrapper.get_current_health() is None
            assert wrapper.get_security_alerts() == []
            assert wrapper.get_metrics_summary() is None

    @pytest.mark.asyncio
    async def test_manual_checks_enabled(self):
        """Test manual health and security checks when monitoring is enabled."""
        with (
            patch(
                "tripsage_core.services.infrastructure.database_wrapper.DatabaseService"
            ),
            patch(
                "tripsage_core.services.infrastructure.database_wrapper.ConsolidatedDatabaseMonitor"
            ) as mock_monitor_class,
        ):
            mock_monitor = Mock()
            mock_monitor.manual_health_check = AsyncMock(return_value="health_result")
            mock_monitor.manual_security_check = AsyncMock()
            mock_monitor.configure_monitoring = Mock()
            mock_monitor_class.return_value = mock_monitor

            wrapper = DatabaseServiceWrapper(self.settings_enabled)

            # Test manual checks
            result = await wrapper.manual_health_check()
            assert result == "health_result"

            await wrapper.manual_security_check()
            mock_monitor.manual_security_check.assert_called_once()

    @pytest.mark.asyncio
    async def test_manual_checks_disabled(self):
        """Test manual checks when monitoring is disabled."""
        with patch(
            "tripsage_core.services.infrastructure.database_wrapper.DatabaseService"
        ):
            wrapper = DatabaseServiceWrapper(self.settings_disabled)

            # Test manual checks return None when disabled
            assert await wrapper.manual_health_check() is None
            assert await wrapper.manual_security_check() is None


class TestGlobalWrapperInstance:
    """Test global wrapper instance management."""

    def teardown_method(self):
        """Clean up global state after each test."""
        # Reset global wrapper
        import tripsage_core.services.infrastructure.database_wrapper as wrapper_module

        wrapper_module._database_wrapper = None

    @pytest.mark.asyncio
    async def test_get_database_wrapper_singleton(self):
        """Test that get_database_wrapper returns singleton."""
        with patch(
            "tripsage_core.services.infrastructure.database_wrapper.DatabaseServiceWrapper"
        ) as mock_wrapper_class:
            mock_wrapper = Mock()
            mock_wrapper.connect = AsyncMock()
            mock_wrapper_class.return_value = mock_wrapper

            wrapper1 = await get_database_wrapper()
            wrapper2 = await get_database_wrapper()

            assert wrapper1 is wrapper2
            mock_wrapper.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_database_wrapper(self):
        """Test closing global wrapper instance."""
        with patch(
            "tripsage_core.services.infrastructure.database_wrapper.DatabaseServiceWrapper"
        ) as mock_wrapper_class:
            mock_wrapper = Mock()
            mock_wrapper.connect = AsyncMock()
            mock_wrapper.close = AsyncMock()
            mock_wrapper_class.return_value = mock_wrapper

            # Get wrapper
            await get_database_wrapper()

            # Close wrapper
            await close_database_wrapper()

            mock_wrapper.close.assert_called_once()

            # Verify global instance was reset
            import tripsage_core.services.infrastructure.database_wrapper as wrapper_module  # noqa: E501

            assert wrapper_module._database_wrapper is None
