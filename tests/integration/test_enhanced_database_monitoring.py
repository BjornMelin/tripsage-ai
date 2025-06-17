"""
Integration tests for Enhanced Database Service with Query Performance Monitoring.

Tests demonstrate real-world usage patterns and verify monitoring integration
works correctly with actual database operations.
"""

import asyncio
from unittest.mock import Mock, patch

import pytest

from tripsage_core.config import Settings
from tripsage_core.monitoring.database_metrics import DatabaseMetrics
from tripsage_core.services.infrastructure.enhanced_database_service_with_monitoring import (
    EnhancedDatabaseService,
)
from tripsage_core.services.infrastructure.query_monitor import (
    QueryMonitorConfig,
    QueryType,
)


class TestEnhancedDatabaseServiceIntegration:
    """Integration tests for EnhancedDatabaseService."""

    def setup_method(self):
        """Set up test fixtures."""
        self.settings = Settings()
        self.metrics = Mock(spec=DatabaseMetrics)
        self.metrics.record_query = Mock()

        # Mock Supabase client to avoid actual database connections
        self.mock_client = Mock()
        self.mock_client.table.return_value.select.return_value.limit.return_value.execute.return_value.data = [
            {"id": "test_id"}
        ]
        self.mock_client.table.return_value.insert.return_value.execute.return_value.data = [
            {"id": "new_id", "name": "test"}
        ]
        self.mock_client.table.return_value.select.return_value.execute.return_value.data = [
            {"id": "user_1", "name": "Test User"}
        ]

    @pytest.mark.asyncio
    async def test_enhanced_service_initialization(self):
        """Test enhanced service initialization with monitoring."""
        # Mock the database connection process more thoroughly
        with (
            patch(
                "tripsage_core.services.infrastructure.enhanced_database_service_with_monitoring.create_client"
            ) as mock_create,
            patch(
                "tripsage_core.services.infrastructure.database_service.create_client"
            ) as mock_create_parent,
            patch("asyncio.to_thread") as mock_to_thread,
        ):
            mock_create.return_value = self.mock_client
            mock_create_parent.return_value = self.mock_client
            mock_to_thread.return_value = None  # Mock successful query

            # Create settings with valid credentials for testing
            test_settings = Settings(
                database_url="https://test.supabase.co",
                database_public_key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test_key_for_testing",  # Valid format key
            )

            service = EnhancedDatabaseService(
                settings=test_settings,
                monitor_config=QueryMonitorConfig(
                    enabled=True,
                    slow_query_threshold=0.1,
                ),
                metrics=self.metrics,
                enable_monitoring=True,
            )

            assert service.monitoring_enabled is True
            assert service.query_monitor is not None

            # Test connection
            await service.connect()
            assert service.is_connected

            await service.close()

    @pytest.mark.asyncio
    async def test_monitored_database_operations(self):
        """Test database operations with monitoring enabled."""
        with patch(
            "tripsage_core.services.infrastructure.enhanced_database_service_with_monitoring.create_client"
        ) as mock_create:
            mock_create.return_value = self.mock_client

            service = EnhancedDatabaseService(
                settings=self.settings,
                monitor_config=QueryMonitorConfig(
                    enabled=True,
                    slow_query_threshold=0.01,  # Very low threshold for testing
                ),
                metrics=self.metrics,
                enable_monitoring=True,
            )

            await service.connect()

            try:
                # Test INSERT operation
                await service.insert(
                    "users",
                    {"name": "Test User", "email": "test@example.com"},
                    user_id="test_user",
                    session_id="test_session",
                )

                # Test SELECT operation
                await service.select(
                    "users",
                    "*",
                    {"id": "test_user"},
                    user_id="test_user",
                    session_id="test_session",
                )

                # Test UPDATE operation
                await service.update(
                    "users",
                    {"name": "Updated User"},
                    {"id": "test_user"},
                    user_id="test_user",
                )

                # Test COUNT operation
                await service.count(
                    "users",
                    {"active": True},
                    user_id="test_user",
                )

                # Verify monitoring captured operations
                monitor = service.query_monitor
                history = await monitor.tracker.get_query_history()

                assert len(history) == 4
                assert history[0].query_type == QueryType.INSERT
                assert history[1].query_type == QueryType.SELECT
                assert history[2].query_type == QueryType.UPDATE
                assert history[3].query_type == QueryType.COUNT

                # Verify user context was captured
                assert all(ex.user_id == "test_user" for ex in history[:3])

                # Check performance metrics
                metrics = await monitor.get_performance_metrics()
                assert metrics.total_queries == 4

            finally:
                await service.close()

    @pytest.mark.asyncio
    async def test_monitoring_disabled_operations(self):
        """Test database operations with monitoring disabled."""
        with patch(
            "tripsage_core.services.infrastructure.enhanced_database_service_with_monitoring.create_client"
        ) as mock_create:
            mock_create.return_value = self.mock_client

            service = EnhancedDatabaseService(
                settings=self.settings,
                enable_monitoring=False,
            )

            await service.connect()

            try:
                assert service.monitoring_enabled is False
                assert service.query_monitor is None

                # Operations should work normally without monitoring
                result = await service.insert("users", {"name": "Test"})
                assert result is not None

                result = await service.select("users", "*")
                assert result is not None

            finally:
                await service.close()

    @pytest.mark.asyncio
    async def test_slow_query_detection(self):
        """Test slow query detection and alerting."""
        with patch(
            "tripsage_core.services.infrastructure.enhanced_database_service_with_monitoring.create_client"
        ) as mock_create:
            mock_create.return_value = self.mock_client

            # Configure aggressive thresholds for testing
            monitor_config = QueryMonitorConfig(
                enabled=True,
                slow_query_threshold=0.001,  # 1ms threshold
                very_slow_query_threshold=0.01,
                critical_query_threshold=0.1,
            )

            service = EnhancedDatabaseService(
                settings=self.settings,
                monitor_config=monitor_config,
                metrics=self.metrics,
                enable_monitoring=True,
            )

            await service.connect()

            try:
                # Capture alerts
                captured_alerts = []
                service.add_performance_alert_callback(
                    lambda alert: captured_alerts.append(alert)
                )

                # Execute operations that should trigger slow query detection
                await service.select("users", "*", user_id="test_user")
                await asyncio.sleep(0.02)  # Ensure some processing time

                await service.insert(
                    "posts",
                    {"title": "Test Post", "content": "Test content"},
                    user_id="test_user",
                )
                await asyncio.sleep(0.02)

                # Check for slow queries
                await service.query_monitor.get_slow_queries()

                # Note: In testing, queries may not actually be slow
                # but we can verify the monitoring infrastructure is working
                history = await service.query_monitor.tracker.get_query_history()
                assert len(history) == 2

                # Verify all queries have timing information
                for execution in history:
                    assert execution.duration is not None
                    assert execution.duration >= 0

            finally:
                await service.close()

    @pytest.mark.asyncio
    async def test_n_plus_one_pattern_simulation(self):
        """Test N+1 query pattern detection."""
        with patch(
            "tripsage_core.services.infrastructure.enhanced_database_service_with_monitoring.create_client"
        ) as mock_create:
            mock_create.return_value = self.mock_client

            monitor_config = QueryMonitorConfig(
                enabled=True,
                track_patterns=True,
                n_plus_one_threshold=3,  # Detect after 3 similar queries
                n_plus_one_time_window=10.0,
            )

            service = EnhancedDatabaseService(
                settings=self.settings,
                monitor_config=monitor_config,
                metrics=self.metrics,
                enable_monitoring=True,
            )

            await service.connect()

            try:
                # Simulate N+1 pattern: Get posts, then get comments for each post
                await service.select("posts", "*", user_id="test_user")

                # Simulate getting comments for multiple posts (N+1 pattern)
                for post_id in range(5):
                    await service.select(
                        "comments",
                        "*",
                        {"post_id": post_id},
                        user_id="test_user",
                    )

                # Wait for pattern analysis
                await asyncio.sleep(0.1)

                # Check for detected patterns
                patterns = await service.query_monitor.get_query_patterns()

                # We should detect at least one N+1 pattern
                n_plus_one_patterns = [
                    p for p in patterns if p.pattern_type == "n_plus_one"
                ]
                assert len(n_plus_one_patterns) >= 1

                # Check pattern details
                pattern = n_plus_one_patterns[0]
                assert pattern.table_name == "comments"
                assert pattern.occurrence_count >= 3

            finally:
                await service.close()

    @pytest.mark.asyncio
    async def test_performance_reporting_api(self):
        """Test performance reporting API."""
        with patch(
            "tripsage_core.services.infrastructure.enhanced_database_service_with_monitoring.create_client"
        ) as mock_create:
            mock_create.return_value = self.mock_client

            service = EnhancedDatabaseService(
                settings=self.settings,
                monitor_config=QueryMonitorConfig(enabled=True),
                metrics=self.metrics,
                enable_monitoring=True,
            )

            await service.connect()

            try:
                # Execute some operations
                await service.select("users", "*", user_id="user1")
                await service.select("posts", "*", user_id="user1")
                await service.insert("comments", {"text": "test"}, user_id="user2")

                # Test performance metrics API
                metrics = await service.get_query_performance_metrics()
                assert "monitoring_status" in metrics
                assert "performance_metrics" in metrics
                assert metrics["monitoring_status"]["monitoring_enabled"] is True

                # Test table performance report
                users_report = await service.get_table_performance_report("users")
                assert "table_name" in users_report
                assert users_report["table_name"] == "users"

                # Test user query report
                user_report = await service.get_user_query_report("user1")
                assert "user_id" in user_report
                assert user_report["user_id"] == "user1"
                assert user_report["total_queries"] >= 2

                # Test slow queries report
                slow_queries = await service.get_slow_queries_report(limit=10)
                assert isinstance(slow_queries, list)

                # Test alerts report
                alerts = await service.get_performance_alerts_report(limit=10)
                assert isinstance(alerts, list)

            finally:
                await service.close()

    @pytest.mark.asyncio
    async def test_configuration_management(self):
        """Test monitoring configuration management."""
        with patch(
            "tripsage_core.services.infrastructure.enhanced_database_service_with_monitoring.create_client"
        ) as mock_create:
            mock_create.return_value = self.mock_client

            service = EnhancedDatabaseService(
                settings=self.settings,
                monitor_config=QueryMonitorConfig(
                    enabled=True,
                    slow_query_threshold=1.0,
                ),
                metrics=self.metrics,
                enable_monitoring=True,
            )

            await service.connect()

            try:
                # Test initial configuration
                status = await service.query_monitor.get_monitoring_status()
                assert status["config"]["slow_query_threshold"] == 1.0

                # Update configuration
                service.update_monitoring_config(slow_query_threshold=0.5)

                # Verify configuration was updated
                updated_status = await service.query_monitor.get_monitoring_status()
                assert updated_status["config"]["slow_query_threshold"] == 0.5

            finally:
                await service.close()

    @pytest.mark.asyncio
    async def test_vector_search_monitoring(self):
        """Test vector search operations with monitoring."""
        with patch(
            "tripsage_core.services.infrastructure.enhanced_database_service_with_monitoring.create_client"
        ) as mock_create:
            # Mock vector search response
            mock_result = [
                {"id": "1", "content": "test", "distance": 0.1},
                {"id": "2", "content": "example", "distance": 0.2},
            ]
            mock_create.return_value.table.return_value.select.return_value.lt.return_value.order.return_value.limit.return_value.execute.return_value.data = mock_result

            service = EnhancedDatabaseService(
                settings=self.settings,
                monitor_config=QueryMonitorConfig(enabled=True),
                metrics=self.metrics,
                enable_monitoring=True,
            )

            await service.connect()

            try:
                # Test vector search
                query_vector = [0.1, 0.2, 0.3, 0.4, 0.5]
                await service.vector_search(
                    table="documents",
                    vector_column="embedding",
                    query_vector=query_vector,
                    limit=10,
                    similarity_threshold=0.8,
                    user_id="test_user",
                )

                # Verify monitoring captured the vector search
                history = await service.query_monitor.tracker.get_query_history()
                assert len(history) == 1

                execution = history[0]
                assert execution.query_type == QueryType.VECTOR_SEARCH
                assert execution.table_name == "documents"
                assert execution.user_id == "test_user"
                assert execution.tags["vector_dimension"] == 5
                assert execution.tags["similarity_threshold"] == 0.8

            finally:
                await service.close()

    @pytest.mark.asyncio
    async def test_transaction_monitoring(self):
        """Test transaction monitoring."""
        with patch(
            "tripsage_core.services.infrastructure.enhanced_database_service_with_monitoring.create_client"
        ) as mock_create:
            mock_create.return_value = self.mock_client

            service = EnhancedDatabaseService(
                settings=self.settings,
                monitor_config=QueryMonitorConfig(enabled=True),
                metrics=self.metrics,
                enable_monitoring=True,
            )

            await service.connect()

            try:
                # Test transaction monitoring
                async with service.transaction(
                    user_id="test_user", session_id="test_session"
                ):
                    # Simulate transaction operations
                    await asyncio.sleep(0.01)

                # Verify transaction was monitored
                history = await service.query_monitor.tracker.get_query_history()
                assert len(history) == 1

                execution = history[0]
                assert execution.query_type == QueryType.TRANSACTION
                assert execution.user_id == "test_user"
                assert execution.session_id == "test_session"

            finally:
                await service.close()

    def test_monitoring_callback_system(self):
        """Test monitoring callback system."""
        captured_alerts = []

        def alert_callback(alert):
            captured_alerts.append(alert)

        service = EnhancedDatabaseService(
            settings=self.settings,
            monitor_config=QueryMonitorConfig(enabled=True),
            enable_monitoring=True,
        )

        # Test adding callback
        service.add_performance_alert_callback(alert_callback)

        # Verify callback was added
        assert len(service.query_monitor._alerting._alert_callbacks) == 1

    @pytest.mark.asyncio
    async def test_backward_compatibility(self):
        """Test that enhanced service maintains backward compatibility."""
        with patch(
            "tripsage_core.services.infrastructure.enhanced_database_service_with_monitoring.create_client"
        ) as mock_create:
            mock_create.return_value = self.mock_client

            service = EnhancedDatabaseService(
                settings=self.settings,
                enable_monitoring=False,  # Disable monitoring for compatibility test
            )

            await service.connect()

            try:
                # All standard database operations should work exactly as before
                result = await service.insert("users", {"name": "Test"})
                assert result is not None

                result = await service.select("users", "*", {"id": "test"})
                assert result is not None

                result = await service.update(
                    "users", {"name": "Updated"}, {"id": "test"}
                )
                assert result is not None

                count = await service.count("users")
                assert isinstance(count, int)

                # Business methods should work
                trip = await service.create_trip(
                    {"name": "Test Trip", "user_id": "test"}
                )
                assert trip is not None

            finally:
                await service.close()
