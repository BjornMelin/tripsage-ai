"""
Comprehensive tests for Essential Query Performance Monitoring System.

Tests cover core components: query tracking, metrics collection, and essential
monitoring following TDD principles.
"""

import asyncio
import time
from unittest.mock import Mock

import pytest

from tripsage_core.config import Settings
from tripsage_core.monitoring.database_metrics import DatabaseMetrics
from tripsage_core.services.infrastructure.query_monitor import (
    MetricsCollector,
    QueryExecution,
    QueryMonitorConfig,
    QueryPerformanceMonitor,
    QueryStatus,
    QueryTracker,
    QueryType,
    get_query_monitor,
    reset_query_monitor,
)


class TestQueryMonitorConfig:
    """Test QueryMonitorConfig Pydantic model."""

    def test_default_configuration(self):
        """Test default configuration values."""
        config = QueryMonitorConfig()

        assert config.enabled is True
        assert config.slow_query_threshold == 1.0
        assert config.max_query_history == 1000
        assert config.error_rate_threshold == 0.05
        assert config.export_metrics is True

    def test_custom_configuration(self):
        """Test custom configuration values."""
        config = QueryMonitorConfig(
            enabled=False,
            slow_query_threshold=0.5,
            max_query_history=500,
            error_rate_threshold=0.10,
            export_metrics=False,
        )

        assert config.enabled is False
        assert config.slow_query_threshold == 0.5
        assert config.max_query_history == 500
        assert config.error_rate_threshold == 0.10
        assert config.export_metrics is False


class TestQueryExecution:
    """Test QueryExecution dataclass."""

    def test_initialization(self):
        """Test QueryExecution initialization."""
        start_time = time.perf_counter()
        execution = QueryExecution(
            query_id="test_query_1",
            query_type=QueryType.SELECT,
            table_name="users",
            start_time=start_time,
        )

        assert execution.query_id == "test_query_1"
        assert execution.query_type == QueryType.SELECT
        assert execution.table_name == "users"
        assert execution.start_time == start_time
        assert execution.status == QueryStatus.SUCCESS

    def test_duration_calculation(self):
        """Test automatic duration calculation."""
        start_time = time.perf_counter()
        end_time = start_time + 1.5

        execution = QueryExecution(
            query_id="test_query_1",
            query_type=QueryType.SELECT,
            table_name="users",
            start_time=start_time,
            end_time=end_time,
        )

        assert execution.duration == 1.5

    def test_is_slow_property(self):
        """Test is_slow method."""
        execution = QueryExecution(
            query_id="test_query_1",
            query_type=QueryType.SELECT,
            table_name="users",
            start_time=time.perf_counter(),
            duration=1.5,
        )

        assert execution.is_slow(1.0) is True

        execution.duration = 0.5
        assert execution.is_slow(1.0) is False

    def test_is_successful_property(self):
        """Test is_successful property."""
        execution = QueryExecution(
            query_id="test_query_1",
            query_type=QueryType.SELECT,
            table_name="users",
            start_time=time.perf_counter(),
            status=QueryStatus.SUCCESS,
        )

        assert execution.is_successful is True

        execution.status = QueryStatus.ERROR
        assert execution.is_successful is False


class TestQueryTracker:
    """Test QueryTracker class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = QueryMonitorConfig(max_query_history=100)
        self.tracker = QueryTracker(self.config)

    @pytest.mark.asyncio
    async def test_start_query(self):
        """Test starting query tracking."""
        query_id = await self.tracker.start_query(
            query_type=QueryType.SELECT,
            table_name="users",
        )

        assert query_id
        assert query_id in self.tracker._active_queries

        execution = self.tracker._active_queries[query_id]
        assert execution.query_type == QueryType.SELECT
        assert execution.table_name == "users"
        assert execution.start_time > 0

    @pytest.mark.asyncio
    async def test_finish_query(self):
        """Test finishing query tracking."""
        # Start query
        query_id = await self.tracker.start_query(
            query_type=QueryType.SELECT,
            table_name="users",
        )

        # Simulate some processing time
        await asyncio.sleep(0.1)

        # Finish query
        execution = await self.tracker.finish_query(
            query_id=query_id,
            status=QueryStatus.SUCCESS,
            row_count=5,
        )

        assert execution is not None
        assert execution.query_id == query_id
        assert execution.status == QueryStatus.SUCCESS
        assert execution.row_count == 5
        assert execution.end_time is not None
        assert execution.duration is not None
        assert execution.duration >= 0.1

        # Query should be removed from active queries
        assert query_id not in self.tracker._active_queries

        # Query should be in history
        assert execution in self.tracker._query_history

    @pytest.mark.asyncio
    async def test_finish_nonexistent_query(self):
        """Test finishing a nonexistent query."""
        execution = await self.tracker.finish_query(
            query_id="nonexistent",
            status=QueryStatus.SUCCESS,
        )

        assert execution is None

    def test_get_query_history(self):
        """Test getting query history."""
        # Add some queries to history
        for i in range(5):
            execution = QueryExecution(
                query_id=f"query_{i}",
                query_type=QueryType.SELECT,
                table_name="users",
                start_time=time.perf_counter(),
                duration=0.1,
            )
            self.tracker._query_history.append(execution)

        history = self.tracker.get_query_history()
        assert len(history) == 5

        # Test with limit
        limited_history = self.tracker.get_query_history(limit=3)
        assert len(limited_history) == 3

    def test_get_slow_queries(self):
        """Test getting slow queries."""
        # Create queries with different durations
        durations = [0.5, 1.5, 2.5, 0.3]
        for i, duration in enumerate(durations):
            execution = QueryExecution(
                query_id=f"query_{i}",
                query_type=QueryType.SELECT,
                table_name="users",
                start_time=time.perf_counter(),
                duration=duration,
            )
            self.tracker._query_history.append(execution)

        # Get slow queries with default threshold (1.0s)
        slow_queries = self.tracker.get_slow_queries()
        assert len(slow_queries) == 2  # 1.5s and 2.5s queries

        # Get slow queries with custom threshold
        slow_queries = self.tracker.get_slow_queries(threshold=2.0)
        assert len(slow_queries) == 1  # Only 2.5s query

    @pytest.mark.asyncio
    async def test_disabled_monitoring(self):
        """Test behavior when monitoring is disabled."""
        self.config.enabled = False

        query_id = await self.tracker.start_query(QueryType.SELECT, "users")
        assert query_id == ""

    @pytest.mark.asyncio
    async def test_history_limit(self):
        """Test query history limit enforcement."""
        self.config.max_query_history = 3

        # Add more queries than the limit
        for _i in range(5):
            query_id = await self.tracker.start_query(QueryType.SELECT, "users")
            await self.tracker.finish_query(query_id, QueryStatus.SUCCESS)

        # History should be limited to max_query_history
        assert len(self.tracker._query_history) == 3


class TestMetricsCollector:
    """Test MetricsCollector class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = QueryMonitorConfig()
        self.collector = MetricsCollector(self.config)

    def create_execution(
        self,
        query_type: QueryType = QueryType.SELECT,
        duration: float = 1.0,
        status: QueryStatus = QueryStatus.SUCCESS,
    ) -> QueryExecution:
        """Helper to create QueryExecution for testing."""
        return QueryExecution(
            query_id=f"query_{int(time.time() * 1000000)}",
            query_type=query_type,
            table_name="users",
            start_time=time.perf_counter(),
            duration=duration,
            status=status,
        )

    def test_calculate_basic_metrics(self):
        """Test basic metrics calculation."""
        executions = [
            self.create_execution(duration=0.5, status=QueryStatus.SUCCESS),
            self.create_execution(duration=1.5, status=QueryStatus.SUCCESS),
            self.create_execution(duration=2.5, status=QueryStatus.ERROR),
            self.create_execution(duration=0.3, status=QueryStatus.SUCCESS),
        ]

        metrics = self.collector.calculate_metrics(executions)

        assert metrics.total_queries == 4
        assert metrics.successful_queries == 3
        assert metrics.failed_queries == 1
        assert metrics.error_rate == 0.25
        assert metrics.slow_queries == 2  # 1.5s and 2.5s queries
        assert abs(metrics.avg_duration - 1.2) < 0.01  # (0.5+1.5+2.5+0.3)/4

    def test_empty_executions(self):
        """Test metrics calculation with empty executions."""
        metrics = self.collector.calculate_metrics([])

        assert metrics.total_queries == 0
        assert metrics.successful_queries == 0
        assert metrics.failed_queries == 0
        assert metrics.error_rate == 0.0
        assert metrics.avg_duration == 0.0


class TestQueryPerformanceMonitor:
    """Test main QueryPerformanceMonitor class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = QueryMonitorConfig(enabled=True)
        self.settings = Settings()
        self.metrics = Mock(spec=DatabaseMetrics)
        self.metrics.record_query = Mock()

        self.monitor = QueryPerformanceMonitor(
            config=self.config,
            settings=self.settings,
            metrics=self.metrics,
        )

    @pytest.mark.asyncio
    async def test_track_and_finish_query(self):
        """Test complete query tracking lifecycle."""
        # Track query
        query_id = await self.monitor.track_query(
            query_type=QueryType.SELECT,
            table_name="users",
        )

        assert query_id

        # Simulate some processing time
        await asyncio.sleep(0.1)

        # Finish query
        execution = await self.monitor.finish_query(
            query_id=query_id,
            status=QueryStatus.SUCCESS,
            row_count=1,
        )

        assert execution is not None
        assert execution.query_type == QueryType.SELECT
        assert execution.table_name == "users"
        assert execution.status == QueryStatus.SUCCESS
        assert execution.row_count == 1
        assert execution.duration >= 0.1

        # Verify metrics were recorded
        self.metrics.record_query.assert_called_once()

    @pytest.mark.asyncio
    async def test_monitor_query_context_manager(self):
        """Test query monitoring context manager."""
        # Test successful query
        async with self.monitor.monitor_query(QueryType.SELECT, "users") as query_id:
            assert query_id
            await asyncio.sleep(0.05)

        # Test query with exception
        with pytest.raises(ValueError):
            async with self.monitor.monitor_query(QueryType.INSERT, "posts"):
                raise ValueError("Database error")

        # Verify both queries were tracked
        history = self.monitor.tracker.get_query_history()
        assert len(history) == 2
        assert history[0].status == QueryStatus.SUCCESS
        assert history[1].status == QueryStatus.ERROR

    def test_get_performance_metrics(self):
        """Test performance metrics retrieval."""
        # Add some test data to history
        durations = [0.5, 1.5, 0.8, 2.0]
        statuses = [
            QueryStatus.SUCCESS,
            QueryStatus.SUCCESS,
            QueryStatus.ERROR,
            QueryStatus.SUCCESS,
        ]

        for duration, status in zip(durations, statuses, strict=True):
            execution = QueryExecution(
                query_id=f"query_{int(time.time() * 1000000)}",
                query_type=QueryType.SELECT,
                table_name="users",
                start_time=time.perf_counter(),
                duration=duration,
                status=status,
            )
            self.monitor.tracker._query_history.append(execution)

        metrics = self.monitor.get_performance_metrics()

        assert metrics.total_queries == 4
        assert metrics.successful_queries == 3
        assert metrics.failed_queries == 1
        assert metrics.slow_queries == 2  # 1.5s and 2.0s
        assert metrics.error_rate == 0.25

    def test_get_slow_queries(self):
        """Test slow queries retrieval."""
        # Add queries with different durations
        durations = [0.5, 1.5, 2.5, 0.3]
        for duration in durations:
            execution = QueryExecution(
                query_id=f"query_{int(time.time() * 1000000)}",
                query_type=QueryType.SELECT,
                table_name="users",
                start_time=time.perf_counter(),
                duration=duration,
            )
            self.monitor.tracker._query_history.append(execution)

        slow_queries = self.monitor.get_slow_queries()
        assert len(slow_queries) == 2  # 1.5s and 2.5s queries

    def test_get_monitoring_status(self):
        """Test monitoring status reporting."""
        # Add some test queries
        execution = QueryExecution(
            query_id="test_query",
            query_type=QueryType.SELECT,
            table_name="users",
            start_time=time.perf_counter(),
            duration=1.5,
        )
        self.monitor.tracker._query_history.append(execution)

        status = self.monitor.get_monitoring_status()

        assert status["monitoring_enabled"] is True
        assert "config" in status
        assert "statistics" in status
        assert status["statistics"]["total_tracked_queries"] == 1

    def test_update_config(self):
        """Test configuration updates."""
        original_threshold = self.monitor.config.slow_query_threshold

        self.monitor.update_config(slow_query_threshold=0.5)

        assert self.monitor.config.slow_query_threshold == 0.5
        assert self.monitor.config.slow_query_threshold != original_threshold

    @pytest.mark.asyncio
    async def test_disabled_monitoring(self):
        """Test behavior when monitoring is disabled."""
        self.monitor.config.enabled = False

        query_id = await self.monitor.track_query(QueryType.SELECT, "users")
        assert query_id == ""

        execution = await self.monitor.finish_query(query_id, QueryStatus.SUCCESS)
        assert execution is None

    @pytest.mark.asyncio
    async def test_error_handling_in_metrics(self):
        """Test error handling when metrics recording fails."""
        # Mock metrics to raise an exception
        self.metrics.record_query.side_effect = Exception("Metrics error")

        query_id = await self.monitor.track_query(QueryType.SELECT, "users")

        # This should not raise an exception despite metrics failure
        execution = await self.monitor.finish_query(query_id, QueryStatus.SUCCESS)

        assert execution is not None
        assert execution.status == QueryStatus.SUCCESS


class TestUtilityFunctions:
    """Test utility functions."""

    def test_global_query_monitor(self):
        """Test global query monitor management."""
        # Reset first
        reset_query_monitor()

        # Get monitor (should create new one)
        monitor1 = get_query_monitor()
        assert monitor1 is not None

        # Get monitor again (should return same instance)
        monitor2 = get_query_monitor()
        assert monitor1 is monitor2

        # Reset and get new monitor
        reset_query_monitor()
        monitor3 = get_query_monitor()
        assert monitor3 is not monitor1


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""

    def setup_method(self):
        """Set up test fixtures."""
        self.monitor = QueryPerformanceMonitor(
            config=QueryMonitorConfig(
                slow_query_threshold=0.05,  # Lower threshold for testing
                error_rate_threshold=0.2,
            )
        )

    @pytest.mark.asyncio
    async def test_comprehensive_monitoring_scenario(self):
        """Test comprehensive monitoring with various query types and patterns."""
        # Execute various types of queries
        query_scenarios = [
            # Normal queries
            {"type": QueryType.SELECT, "table": "users", "duration": 0.05},
            {"type": QueryType.INSERT, "table": "posts", "duration": 0.08},
            {"type": QueryType.UPDATE, "table": "users", "duration": 0.06},
            # Slow queries
            {"type": QueryType.SELECT, "table": "large_table", "duration": 0.15},
            {"type": QueryType.COUNT, "table": "analytics", "duration": 0.25},
            # Failed queries
            {
                "type": QueryType.DELETE,
                "table": "posts",
                "duration": 0.03,
                "status": QueryStatus.ERROR,
            },
        ]

        for scenario in query_scenarios:
            query_id = await self.monitor.track_query(
                query_type=scenario["type"],
                table_name=scenario["table"],
            )

            await asyncio.sleep(scenario["duration"])

            await self.monitor.finish_query(
                query_id=query_id,
                status=scenario.get("status", QueryStatus.SUCCESS),
                error_message="Test error"
                if scenario.get("status") == QueryStatus.ERROR
                else None,
            )

        # Verify comprehensive tracking
        status = self.monitor.get_monitoring_status()
        assert status["statistics"]["total_tracked_queries"] == len(query_scenarios)

        # Verify metrics calculation
        metrics = self.monitor.get_performance_metrics()
        assert metrics.total_queries == len(query_scenarios)
        assert metrics.failed_queries == 1
        assert metrics.slow_queries >= 2  # The slow queries

        # Verify slow queries detection
        slow_queries = self.monitor.get_slow_queries()
        assert len(slow_queries) >= 2

    @pytest.mark.asyncio
    async def test_performance_monitoring_over_time(self):
        """Test performance monitoring over multiple queries."""
        # Execute queries with varying performance
        for i in range(10):
            duration = 0.05 + (i * 0.02)  # Gradually increasing duration
            status = QueryStatus.ERROR if i % 5 == 0 else QueryStatus.SUCCESS

            query_id = await self.monitor.track_query(QueryType.SELECT, "users")
            await asyncio.sleep(duration)
            await self.monitor.finish_query(
                query_id,
                status,
                "Error" if status == QueryStatus.ERROR else None,
            )

        metrics = self.monitor.get_performance_metrics()
        assert metrics.total_queries == 10
        assert metrics.error_rate == 0.2  # 2 errors out of 10
        assert metrics.avg_duration > 0.05
        assert metrics.slow_queries > 0  # Some queries should be slow
