"""
Comprehensive tests for Query Performance Monitoring System.

Tests cover all components including query tracking, pattern detection,
performance analytics, alerting, and integration features following TDD principles.
"""

import asyncio
import time
from datetime import datetime, timedelta, timezone
from typing import Optional
from unittest.mock import Mock, patch

import pytest

from tripsage_core.config import Settings
from tripsage_core.monitoring.database_metrics import DatabaseMetrics
from tripsage_core.services.infrastructure.query_monitor import (
    AlertingSystem,
    AlertSeverity,
    AlertType,
    PerformanceAlert,
    PerformanceAnalytics,
    PerformanceMetrics,
    QueryExecution,
    QueryExecutionTracker,
    QueryMonitorConfig,
    QueryPattern,
    QueryPatternDetector,
    QueryPerformanceMonitor,
    QueryStatus,
    QueryType,
    create_table_extractor,
    create_user_extractor,
    get_query_monitor,
    reset_query_monitor,
)


class TestQueryMonitorConfig:
    """Test QueryMonitorConfig Pydantic model."""

    def test_default_configuration(self):
        """Test default configuration values."""
        config = QueryMonitorConfig()

        assert config.enabled is True
        assert config.track_patterns is True
        assert config.collect_stack_traces is True
        assert config.slow_query_threshold == 1.0
        assert config.very_slow_query_threshold == 5.0
        assert config.critical_query_threshold == 10.0
        assert config.n_plus_one_threshold == 10
        assert config.error_rate_threshold == 0.05
        assert config.export_prometheus is True

    def test_custom_configuration(self):
        """Test custom configuration values."""
        config = QueryMonitorConfig(
            enabled=False,
            slow_query_threshold=0.5,
            very_slow_query_threshold=2.0,
            critical_query_threshold=5.0,
            n_plus_one_threshold=5,
            error_rate_threshold=0.10,
        )

        assert config.enabled is False
        assert config.slow_query_threshold == 0.5
        assert config.very_slow_query_threshold == 2.0
        assert config.critical_query_threshold == 5.0
        assert config.n_plus_one_threshold == 5
        assert config.error_rate_threshold == 0.10

    def test_threshold_validation(self):
        """Test threshold validation rules."""
        # Valid thresholds
        config = QueryMonitorConfig(
            slow_query_threshold=1.0,
            very_slow_query_threshold=2.0,
            critical_query_threshold=3.0,
        )
        assert config.slow_query_threshold == 1.0
        assert config.very_slow_query_threshold == 2.0
        assert config.critical_query_threshold == 3.0

        # Invalid thresholds should raise validation errors
        with pytest.raises(ValueError, match="very_slow_query_threshold must be"):
            QueryMonitorConfig(
                slow_query_threshold=2.0,
                very_slow_query_threshold=1.0,  # Must be > slow
            )

        with pytest.raises(ValueError, match="critical_query_threshold must be"):
            QueryMonitorConfig(
                very_slow_query_threshold=2.0,
                critical_query_threshold=1.0,  # Must be > very_slow
            )


class TestQueryExecution:
    """Test QueryExecution dataclass."""

    def test_initialization(self):
        """Test QueryExecution initialization."""
        start_time = time.perf_counter()
        execution = QueryExecution(
            query_id="test_query_1",
            query_type=QueryType.SELECT,
            table_name="users",
            query_hash="hash123",
            query_text="SELECT * FROM users",
            start_time=start_time,
        )

        assert execution.query_id == "test_query_1"
        assert execution.query_type == QueryType.SELECT
        assert execution.table_name == "users"
        assert execution.query_hash == "hash123"
        assert execution.query_text == "SELECT * FROM users"
        assert execution.start_time == start_time
        assert execution.status == QueryStatus.SUCCESS
        assert isinstance(execution.timestamp, datetime)

    def test_duration_calculation(self):
        """Test automatic duration calculation."""
        start_time = time.perf_counter()
        end_time = start_time + 1.5

        execution = QueryExecution(
            query_id="test_query_1",
            query_type=QueryType.SELECT,
            table_name="users",
            query_hash="hash123",
            query_text="SELECT * FROM users",
            start_time=start_time,
            end_time=end_time,
        )

        assert execution.duration == 1.5

    def test_is_slow_property(self):
        """Test is_slow property."""
        execution = QueryExecution(
            query_id="test_query_1",
            query_type=QueryType.SELECT,
            table_name="users",
            query_hash="hash123",
            query_text="SELECT * FROM users",
            start_time=time.perf_counter(),
            duration=1.5,
        )

        assert execution.is_slow is True

        execution.duration = 0.5
        assert execution.is_slow is False

    def test_is_successful_property(self):
        """Test is_successful property."""
        execution = QueryExecution(
            query_id="test_query_1",
            query_type=QueryType.SELECT,
            table_name="users",
            query_hash="hash123",
            query_text="SELECT * FROM users",
            start_time=time.perf_counter(),
            status=QueryStatus.SUCCESS,
        )

        assert execution.is_successful is True

        execution.status = QueryStatus.ERROR
        assert execution.is_successful is False


class TestQueryExecutionTracker:
    """Test QueryExecutionTracker class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = QueryMonitorConfig(max_query_history=100)
        self.tracker = QueryExecutionTracker(self.config)

    @pytest.mark.asyncio
    async def test_start_query(self):
        """Test starting query tracking."""
        query_id = await self.tracker.start_query(
            query_type=QueryType.SELECT,
            table_name="users",
            query_text="SELECT * FROM users WHERE id = ?",
            user_id="user123",
            session_id="session456",
            tags={"test": True},
        )

        assert query_id
        assert query_id in self.tracker._active_queries

        execution = self.tracker._active_queries[query_id]
        assert execution.query_type == QueryType.SELECT
        assert execution.table_name == "users"
        assert execution.query_text == "SELECT * FROM users WHERE id = ?"
        assert execution.user_id == "user123"
        assert execution.session_id == "session456"
        assert execution.tags["test"] is True
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

    @pytest.mark.asyncio
    async def test_query_hash_generation(self):
        """Test query hash generation for pattern detection."""
        # Same query type and table should generate same hash
        hash1 = self.tracker._generate_query_hash(
            QueryType.SELECT, "users", "SELECT * FROM users WHERE id = 1"
        )
        hash2 = self.tracker._generate_query_hash(
            QueryType.SELECT, "users", "SELECT * FROM users WHERE id = 2"
        )

        # Hashes should be the same (normalized)
        assert hash1 == hash2

        # Different table should generate different hash
        hash3 = self.tracker._generate_query_hash(
            QueryType.SELECT, "posts", "SELECT * FROM posts WHERE id = 1"
        )

        assert hash1 != hash3

    def test_normalize_query_text(self):
        """Test query text normalization."""
        original = "SELECT * FROM users WHERE id = 123 AND name = 'John Doe'"
        normalized = self.tracker._normalize_query_text(original)
        expected = "select * from users where id = ? and name = '?'"

        assert normalized == expected

    @pytest.mark.asyncio
    async def test_get_active_queries(self):
        """Test getting active queries."""
        # Start multiple queries
        query_id1 = await self.tracker.start_query(QueryType.SELECT, "users")
        query_id2 = await self.tracker.start_query(QueryType.INSERT, "posts")

        active_queries = await self.tracker.get_active_queries()

        assert len(active_queries) == 2
        query_ids = [ex.query_id for ex in active_queries]
        assert query_id1 in query_ids
        assert query_id2 in query_ids

    @pytest.mark.asyncio
    async def test_get_query_history(self):
        """Test getting query history."""
        # Start and finish multiple queries
        for i in range(5):
            query_id = await self.tracker.start_query(
                QueryType.SELECT, "users", user_id=f"user{i}"
            )
            await self.tracker.finish_query(query_id, QueryStatus.SUCCESS)

        history = await self.tracker.get_query_history()
        assert len(history) == 5

        # Test with limit
        limited_history = await self.tracker.get_query_history(limit=3)
        assert len(limited_history) == 3

    @pytest.mark.asyncio
    async def test_get_slow_queries(self):
        """Test getting slow queries."""
        # Create some queries with different durations
        durations = [0.5, 1.5, 2.5, 0.3]
        for _i, duration in enumerate(durations):
            query_id = await self.tracker.start_query(QueryType.SELECT, "users")
            execution = await self.tracker.finish_query(query_id, QueryStatus.SUCCESS)
            # Manually set duration for testing
            execution.duration = duration

        # Get slow queries with default threshold (1.0s)
        slow_queries = await self.tracker.get_slow_queries()
        assert len(slow_queries) == 2  # 1.5s and 2.5s queries

        # Get slow queries with custom threshold
        slow_queries = await self.tracker.get_slow_queries(threshold=2.0)
        assert len(slow_queries) == 1  # Only 2.5s query


class TestQueryPatternDetector:
    """Test QueryPatternDetector class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = QueryMonitorConfig(
            n_plus_one_threshold=3,
            n_plus_one_time_window=10.0,
        )
        self.detector = QueryPatternDetector(self.config)

    @pytest.mark.asyncio
    async def test_n_plus_one_detection(self):
        """Test N+1 query pattern detection."""
        # Create multiple similar queries
        query_hash = "test_hash_123"

        for i in range(5):
            execution = QueryExecution(
                query_id=f"query_{i}",
                query_type=QueryType.SELECT,
                table_name="users",
                query_hash=query_hash,
                query_text="SELECT * FROM users WHERE id = ?",
                start_time=time.perf_counter(),
                duration=0.1,
                status=QueryStatus.SUCCESS,
            )

            patterns = await self.detector.analyze_query(execution)

            if i >= 2:  # Should detect N+1 after 3rd query (threshold = 3)
                assert len(patterns) == 1
                pattern = patterns[0]
                assert pattern.pattern_type == "n_plus_one"
                assert pattern.query_hash == query_hash
                assert pattern.table_name == "users"
                assert pattern.occurrence_count >= 3
                assert pattern.severity == AlertSeverity.WARNING
            else:
                assert len(patterns) == 0

    @pytest.mark.asyncio
    async def test_n_plus_one_time_window_cleanup(self):
        """Test N+1 detection time window cleanup."""
        query_hash = "test_hash_123"

        # Mock time to control time window
        with patch("time.time") as mock_time:
            # Start with time 0
            mock_time.return_value = 0.0

            # Add queries within threshold
            for i in range(3):
                execution = QueryExecution(
                    query_id=f"query_{i}",
                    query_type=QueryType.SELECT,
                    table_name="users",
                    query_hash=query_hash,
                    query_text="SELECT * FROM users WHERE id = ?",
                    start_time=time.perf_counter(),
                )
                await self.detector.analyze_query(execution)

            # Move time forward beyond window
            mock_time.return_value = 15.0  # Beyond 10s window

            # Add another query - should not trigger N+1 due to cleanup
            execution = QueryExecution(
                query_id="query_3",
                query_type=QueryType.SELECT,
                table_name="users",
                query_hash=query_hash,
                query_text="SELECT * FROM users WHERE id = ?",
                start_time=time.perf_counter(),
            )
            patterns = await self.detector.analyze_query(execution)
            assert len(patterns) == 0

    @pytest.mark.asyncio
    async def test_pattern_history(self):
        """Test pattern detection history."""
        # Generate patterns
        for i in range(3):
            query_hash = f"hash_{i}"
            for j in range(4):  # Exceed threshold
                execution = QueryExecution(
                    query_id=f"query_{i}_{j}",
                    query_type=QueryType.SELECT,
                    table_name=f"table_{i}",
                    query_hash=query_hash,
                    query_text=f"SELECT * FROM table_{i}",
                    start_time=time.perf_counter(),
                )
                await self.detector.analyze_query(execution)

        patterns = await self.detector.get_detected_patterns()
        assert len(patterns) >= 3  # At least one pattern per table


class TestPerformanceAnalytics:
    """Test PerformanceAnalytics class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = QueryMonitorConfig()
        self.analytics = PerformanceAnalytics(self.config)

    def create_execution(
        self,
        query_type: QueryType = QueryType.SELECT,
        table_name: str = "users",
        duration: float = 1.0,
        status: QueryStatus = QueryStatus.SUCCESS,
        timestamp: Optional[datetime] = None,
    ) -> QueryExecution:
        """Helper to create QueryExecution for testing."""
        return QueryExecution(
            query_id=f"query_{int(time.time() * 1000000)}",
            query_type=query_type,
            table_name=table_name,
            query_hash="test_hash",
            query_text="SELECT * FROM table",
            start_time=time.perf_counter(),
            duration=duration,
            status=status,
            timestamp=timestamp or datetime.now(timezone.utc),
        )

    @pytest.mark.asyncio
    async def test_calculate_basic_metrics(self):
        """Test basic metrics calculation."""
        executions = [
            self.create_execution(duration=0.5, status=QueryStatus.SUCCESS),
            self.create_execution(duration=1.5, status=QueryStatus.SUCCESS),
            self.create_execution(duration=2.5, status=QueryStatus.ERROR),
            self.create_execution(duration=0.3, status=QueryStatus.SUCCESS),
        ]

        metrics = await self.analytics.calculate_metrics(executions)

        assert metrics.total_queries == 4
        assert metrics.successful_queries == 3
        assert metrics.failed_queries == 1
        assert metrics.error_rate == 0.25
        assert metrics.slow_queries == 2  # 1.5s and 2.5s queries
        assert abs(metrics.avg_duration - 1.2) < 0.01  # (0.5+1.5+2.5+0.3)/4

    @pytest.mark.asyncio
    async def test_calculate_percentile_metrics(self):
        """Test percentile metrics calculation."""
        durations = [0.1, 0.2, 0.3, 0.5, 1.0, 1.5, 2.0, 3.0, 5.0, 10.0]
        executions = [self.create_execution(duration=d) for d in durations]

        metrics = await self.analytics.calculate_metrics(executions)

        assert metrics.p95_duration == 5.0  # 95th percentile
        assert metrics.p99_duration == 10.0  # 99th percentile

    @pytest.mark.asyncio
    async def test_table_statistics(self):
        """Test per-table statistics calculation."""
        executions = [
            self.create_execution(table_name="users", duration=1.0),
            self.create_execution(table_name="users", duration=2.0),
            self.create_execution(table_name="posts", duration=0.5),
            self.create_execution(
                table_name="posts", duration=1.5, status=QueryStatus.ERROR
            ),
        ]

        metrics = await self.analytics.calculate_metrics(executions)

        # Check users table stats
        users_stats = metrics.table_stats["users"]
        assert users_stats["query_count"] == 2
        assert users_stats["error_count"] == 0
        assert users_stats["avg_duration"] == 1.5
        assert users_stats["error_rate"] == 0.0

        # Check posts table stats
        posts_stats = metrics.table_stats["posts"]
        assert posts_stats["query_count"] == 2
        assert posts_stats["error_count"] == 1
        assert posts_stats["avg_duration"] == 1.0
        assert posts_stats["error_rate"] == 0.5

    @pytest.mark.asyncio
    async def test_operation_statistics(self):
        """Test per-operation statistics calculation."""
        executions = [
            self.create_execution(query_type=QueryType.SELECT, duration=1.0),
            self.create_execution(query_type=QueryType.SELECT, duration=2.0),
            self.create_execution(query_type=QueryType.INSERT, duration=0.5),
            self.create_execution(
                query_type=QueryType.INSERT, duration=1.5, status=QueryStatus.ERROR
            ),
        ]

        metrics = await self.analytics.calculate_metrics(executions)

        # Check SELECT stats
        select_stats = metrics.operation_stats["SELECT"]
        assert select_stats["query_count"] == 2
        assert select_stats["error_count"] == 0
        assert select_stats["avg_duration"] == 1.5

        # Check INSERT stats
        insert_stats = metrics.operation_stats["INSERT"]
        assert insert_stats["query_count"] == 2
        assert insert_stats["error_count"] == 1
        assert insert_stats["error_rate"] == 0.5

    @pytest.mark.asyncio
    async def test_trending_data_update(self):
        """Test trending data updates."""
        metrics = PerformanceMetrics(
            total_queries=100,
            avg_duration=1.5,
            error_rate=0.05,
            slow_queries=10,
        )

        await self.analytics.update_trending_data(metrics)

        assert len(metrics.trending_data) == 1
        trend_point = metrics.trending_data[0]
        assert trend_point["avg_duration"] == 1.5
        assert trend_point["error_rate"] == 0.05
        assert trend_point["slow_query_rate"] == 0.1

    @pytest.mark.asyncio
    async def test_performance_degradation_detection(self):
        """Test performance degradation detection."""
        # Set up baseline trending data
        current_time = datetime.now(timezone.utc)
        baseline_time = current_time - timedelta(hours=2)

        # Add baseline data points
        for i in range(5):
            trend_point = {
                "timestamp": baseline_time + timedelta(minutes=i * 10),
                "avg_duration": 1.0,  # Baseline: 1 second
                "error_rate": 0.01,  # Baseline: 1% error rate
            }
            self.analytics._trending_data["overall"].append(trend_point)

        # Test with degraded performance
        degraded_metrics = PerformanceMetrics(
            avg_duration=2.0,  # 100% increase (exceeds 50% threshold)
            error_rate=0.02,
        )

        is_degraded = await self.analytics.detect_performance_degradation(
            degraded_metrics
        )
        assert is_degraded is True

        # Test with normal performance
        normal_metrics = PerformanceMetrics(
            avg_duration=1.2,  # 20% increase (below 50% threshold)
            error_rate=0.02,
        )

        is_degraded = await self.analytics.detect_performance_degradation(
            normal_metrics
        )
        assert is_degraded is False


class TestAlertingSystem:
    """Test AlertingSystem class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = QueryMonitorConfig(
            slow_query_threshold=1.0,
            very_slow_query_threshold=5.0,
            critical_query_threshold=10.0,
            error_rate_threshold=0.05,
        )
        self.alerting = AlertingSystem(self.config)

    def create_execution(
        self,
        duration: float = 1.0,
        status: QueryStatus = QueryStatus.SUCCESS,
        table_name: str = "users",
    ) -> QueryExecution:
        """Helper to create QueryExecution for testing."""
        return QueryExecution(
            query_id="test_query",
            query_type=QueryType.SELECT,
            table_name=table_name,
            query_hash="test_hash",
            query_text="SELECT * FROM users",
            start_time=time.perf_counter(),
            duration=duration,
            status=status,
        )

    @pytest.mark.asyncio
    async def test_slow_query_alert_warning(self):
        """Test slow query alert generation - warning level."""
        execution = self.create_execution(duration=2.0)  # Between 1.0 and 5.0

        alert = await self.alerting._check_slow_query_alert(execution)

        assert alert is not None
        assert alert.alert_type == AlertType.SLOW_QUERY
        assert alert.severity == AlertSeverity.WARNING
        assert alert.duration == 2.0
        assert "2.000s" in alert.message

    @pytest.mark.asyncio
    async def test_slow_query_alert_error(self):
        """Test slow query alert generation - error level."""
        execution = self.create_execution(duration=7.0)  # Between 5.0 and 10.0

        alert = await self.alerting._check_slow_query_alert(execution)

        assert alert is not None
        assert alert.alert_type == AlertType.SLOW_QUERY
        assert alert.severity == AlertSeverity.ERROR
        assert alert.duration == 7.0

    @pytest.mark.asyncio
    async def test_slow_query_alert_critical(self):
        """Test slow query alert generation - critical level."""
        execution = self.create_execution(duration=15.0)  # Above 10.0

        alert = await self.alerting._check_slow_query_alert(execution)

        assert alert is not None
        assert alert.alert_type == AlertType.SLOW_QUERY
        assert alert.severity == AlertSeverity.CRITICAL
        assert alert.duration == 15.0

    @pytest.mark.asyncio
    async def test_no_slow_query_alert(self):
        """Test no alert for fast queries."""
        execution = self.create_execution(duration=0.5)  # Below threshold

        alert = await self.alerting._check_slow_query_alert(execution)

        assert alert is None

    @pytest.mark.asyncio
    async def test_n_plus_one_pattern_alert(self):
        """Test N+1 pattern alert generation."""
        pattern = QueryPattern(
            pattern_id="test_pattern",
            pattern_type="n_plus_one",
            query_hash="test_hash",
            table_name="users",
            occurrence_count=15,
            time_window=60.0,
            first_occurrence=datetime.now(timezone.utc) - timedelta(minutes=1),
            last_occurrence=datetime.now(timezone.utc),
            severity=AlertSeverity.WARNING,
            sample_query="SELECT * FROM users WHERE id = ?",
        )

        alert = await self.alerting._check_pattern_alert(pattern)

        assert alert is not None
        assert alert.alert_type == AlertType.N_PLUS_ONE
        assert alert.severity == AlertSeverity.WARNING
        assert "15 similar queries" in alert.message
        assert alert.table_name == "users"

    @pytest.mark.asyncio
    async def test_high_error_rate_alert(self):
        """Test high error rate alert generation."""
        metrics = PerformanceMetrics(
            total_queries=100,
            failed_queries=10,
            error_rate=0.10,  # 10% > 5% threshold
        )

        alert = await self.alerting._check_error_rate_alert(metrics)

        assert alert is not None
        assert alert.alert_type == AlertType.HIGH_ERROR_RATE
        assert alert.severity == AlertSeverity.ERROR
        assert "10.0%" in alert.message

    @pytest.mark.asyncio
    async def test_no_error_rate_alert(self):
        """Test no alert for normal error rate."""
        metrics = PerformanceMetrics(
            total_queries=100,
            failed_queries=2,
            error_rate=0.02,  # 2% < 5% threshold
        )

        alert = await self.alerting._check_error_rate_alert(metrics)

        assert alert is None

    @pytest.mark.asyncio
    async def test_alert_callback_system(self):
        """Test alert callback system."""
        callback_mock = Mock()
        self.alerting.add_alert_callback(callback_mock)

        alert = PerformanceAlert(
            alert_id="test_alert",
            alert_type=AlertType.SLOW_QUERY,
            severity=AlertSeverity.WARNING,
            message="Test alert",
            details={},
        )

        await self.alerting._process_alert(alert)

        # Verify callback was called
        callback_mock.assert_called_once_with(alert)

        # Verify alert was stored
        alerts = await self.alerting.get_alerts()
        assert len(alerts) == 1
        assert alerts[0] == alert

    @pytest.mark.asyncio
    async def test_alert_filtering(self):
        """Test alert filtering by severity and type."""
        # Create different types of alerts
        alerts = [
            PerformanceAlert(
                alert_id="alert_1",
                alert_type=AlertType.SLOW_QUERY,
                severity=AlertSeverity.WARNING,
                message="Slow query",
                details={},
            ),
            PerformanceAlert(
                alert_id="alert_2",
                alert_type=AlertType.N_PLUS_ONE,
                severity=AlertSeverity.ERROR,
                message="N+1 pattern",
                details={},
            ),
            PerformanceAlert(
                alert_id="alert_3",
                alert_type=AlertType.SLOW_QUERY,
                severity=AlertSeverity.CRITICAL,
                message="Very slow query",
                details={},
            ),
        ]

        for alert in alerts:
            await self.alerting._process_alert(alert)

        # Test filtering by severity
        warning_alerts = await self.alerting.get_alerts(severity=AlertSeverity.WARNING)
        assert len(warning_alerts) == 1
        assert warning_alerts[0].alert_id == "alert_1"

        # Test filtering by type
        slow_query_alerts = await self.alerting.get_alerts(
            alert_type=AlertType.SLOW_QUERY
        )
        assert len(slow_query_alerts) == 2

        # Test filtering by both
        critical_slow_alerts = await self.alerting.get_alerts(
            severity=AlertSeverity.CRITICAL, alert_type=AlertType.SLOW_QUERY
        )
        assert len(critical_slow_alerts) == 1
        assert critical_slow_alerts[0].alert_id == "alert_3"


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
    async def test_start_stop_monitoring(self):
        """Test starting and stopping monitoring."""
        assert not self.monitor._monitoring

        await self.monitor.start_monitoring()
        assert self.monitor._monitoring
        assert self.monitor._analytics_task is not None

        await self.monitor.stop_monitoring()
        assert not self.monitor._monitoring

    @pytest.mark.asyncio
    async def test_track_and_finish_query(self):
        """Test complete query tracking lifecycle."""
        # Track query
        query_id = await self.monitor.track_query(
            query_type=QueryType.SELECT,
            table_name="users",
            query_text="SELECT * FROM users WHERE id = ?",
            user_id="user123",
            session_id="session456",
            tags={"test": True},
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
        assert execution.user_id == "user123"
        assert execution.status == QueryStatus.SUCCESS
        assert execution.row_count == 1
        assert execution.duration >= 0.1

        # Verify Prometheus metrics were updated
        self.metrics.record_query.assert_called_once()

    @pytest.mark.asyncio
    async def test_monitor_query_context_manager(self):
        """Test query monitoring context manager."""
        # Test successful query
        async with self.monitor.monitor_query(
            QueryType.SELECT, "users", user_id="user123"
        ) as query_id:
            assert query_id
            await asyncio.sleep(0.05)  # Simulate query execution

        # Test query with exception
        with pytest.raises(ValueError):
            async with self.monitor.monitor_query(
                QueryType.INSERT, "posts"
            ) as query_id:
                assert query_id
                raise ValueError("Database error")

        # Verify both queries were tracked
        history = await self.monitor.tracker.get_query_history()
        assert len(history) == 2
        assert history[0].status == QueryStatus.SUCCESS
        assert history[1].status == QueryStatus.ERROR

    def test_monitor_query_method_decorator(self):
        """Test query method decorator."""

        # Create a mock database class with decorated method
        class MockDB:
            def __init__(self, monitor):
                self.monitor = monitor

            @self.monitor.monitor_query_method(
                QueryType.SELECT,
                extract_table_from_args=create_table_extractor(0),
                extract_user_from_args=create_user_extractor("user_id"),
            )
            async def select_user(self, table, user_id):
                await asyncio.sleep(0.05)
                return {"id": user_id, "name": "Test User"}

        # Test the decorated method
        async def test_decorated_method():
            db = MockDB(self.monitor)
            result = await db.select_user("users", user_id="user123")

            assert result["id"] == "user123"

            # Verify query was tracked
            history = await self.monitor.tracker.get_query_history()
            assert len(history) == 1
            execution = history[0]
            assert execution.query_type == QueryType.SELECT
            assert execution.table_name == "users"
            assert execution.tags["method"] == "select_user"

        # Run the test
        asyncio.run(test_decorated_method())

    @pytest.mark.asyncio
    async def test_hook_system(self):
        """Test pre and post query hooks."""
        pre_hook_calls = []
        post_hook_calls = []

        def pre_hook(query_type, table_name, query_text, user_id, session_id, tags):
            pre_hook_calls.append(
                {
                    "query_type": query_type,
                    "table_name": table_name,
                    "user_id": user_id,
                }
            )

        def post_hook(execution, patterns, alerts):
            post_hook_calls.append(
                {
                    "query_id": execution.query_id,
                    "duration": execution.duration,
                    "patterns": len(patterns),
                    "alerts": len(alerts),
                }
            )

        # Add hooks
        self.monitor.add_pre_query_hook(pre_hook)
        self.monitor.add_post_query_hook(post_hook)

        # Execute query
        async with self.monitor.monitor_query(
            QueryType.SELECT, "users", user_id="user123"
        ):
            await asyncio.sleep(0.05)

        # Verify hooks were called
        assert len(pre_hook_calls) == 1
        assert pre_hook_calls[0]["query_type"] == QueryType.SELECT
        assert pre_hook_calls[0]["table_name"] == "users"
        assert pre_hook_calls[0]["user_id"] == "user123"

        assert len(post_hook_calls) == 1
        assert post_hook_calls[0]["duration"] >= 0.05

    @pytest.mark.asyncio
    async def test_monitoring_status(self):
        """Test monitoring status reporting."""
        # Start monitoring
        await self.monitor.start_monitoring()

        # Execute some queries
        for _i in range(3):
            async with self.monitor.monitor_query(QueryType.SELECT, "users"):
                await asyncio.sleep(0.01)

        status = await self.monitor.get_monitoring_status()

        assert status["monitoring_enabled"] is True
        assert status["monitoring_active"] is True
        assert status["statistics"]["total_tracked_queries"] == 3
        assert "config" in status
        assert "slow_query_threshold" in status["config"]

        await self.monitor.stop_monitoring()

    @pytest.mark.asyncio
    async def test_performance_metrics_retrieval(self):
        """Test performance metrics retrieval."""
        # Execute queries with different characteristics
        queries = [
            {"duration": 0.5, "status": QueryStatus.SUCCESS},
            {"duration": 1.5, "status": QueryStatus.SUCCESS},  # Slow
            {"duration": 0.8, "status": QueryStatus.ERROR},
            {"duration": 2.0, "status": QueryStatus.SUCCESS},  # Slow
        ]

        for query_config in queries:
            query_id = await self.monitor.track_query(QueryType.SELECT, "users")
            await self.monitor.finish_query(
                query_id=query_id,
                status=query_config["status"],
            )
            # Manually set duration for testing
            execution = self.monitor.tracker._query_history[-1]
            execution.duration = query_config["duration"]

        metrics = await self.monitor.get_performance_metrics()

        assert metrics.total_queries == 4
        assert metrics.successful_queries == 3
        assert metrics.failed_queries == 1
        assert metrics.slow_queries == 2
        assert metrics.error_rate == 0.25

    @pytest.mark.asyncio
    async def test_table_performance_analysis(self):
        """Test table-specific performance analysis."""
        # Execute queries on different tables
        tables = ["users", "posts", "users", "comments", "users"]

        for table in tables:
            async with self.monitor.monitor_query(QueryType.SELECT, table):
                await asyncio.sleep(0.01)

        # Get performance for users table
        users_perf = await self.monitor.get_table_performance("users")

        assert users_perf["table_name"] == "users"
        assert users_perf["total_queries"] == 3
        assert "avg_duration" in users_perf
        assert "error_rate" in users_perf

    @pytest.mark.asyncio
    async def test_user_query_statistics(self):
        """Test user-specific query statistics."""
        users = ["user1", "user2", "user1", "user3", "user1"]

        for user_id in users:
            async with self.monitor.monitor_query(
                QueryType.SELECT, "users", user_id=user_id
            ):
                await asyncio.sleep(0.01)

        # Get stats for user1
        user1_stats = await self.monitor.get_user_query_stats("user1")

        assert user1_stats["user_id"] == "user1"
        assert user1_stats["total_queries"] == 3
        assert "SELECT" in user1_stats["query_types"]

    def test_config_updates(self):
        """Test configuration updates."""
        original_threshold = self.monitor.config.slow_query_threshold

        self.monitor.update_config(slow_query_threshold=0.5)

        assert self.monitor.config.slow_query_threshold == 0.5
        assert self.monitor.config.slow_query_threshold != original_threshold

    @pytest.mark.asyncio
    async def test_disabled_monitoring(self):
        """Test behavior when monitoring is disabled."""
        # Disable monitoring
        self.monitor.config.enabled = False

        query_id = await self.monitor.track_query(QueryType.SELECT, "users")

        # Should return empty string when disabled
        assert query_id == ""

        execution = await self.monitor.finish_query(query_id, QueryStatus.SUCCESS)

        # Should return None when disabled
        assert execution is None


class TestUtilityFunctions:
    """Test utility functions."""

    def test_create_table_extractor(self):
        """Test table name extractor creation."""
        extractor = create_table_extractor(table_arg_index=0)

        # Test with self, table_name arguments
        table_name = extractor("self", "users", "id=123")
        assert table_name == "users"

        # Test with insufficient arguments
        table_name = extractor("self")
        assert table_name is None

    def test_create_user_extractor(self):
        """Test user ID extractor creation."""
        extractor = create_user_extractor("user_id")

        # Test with user_id in kwargs
        user_id = extractor("self", "table", user_id="user123")
        assert user_id == "user123"

        # Test without user_id
        user_id = extractor("self", "table")
        assert user_id is None

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
                slow_query_threshold=0.1,
                n_plus_one_threshold=3,
                error_rate_threshold=0.2,
            )
        )

    @pytest.mark.asyncio
    async def test_n_plus_one_detection_scenario(self):
        """Test realistic N+1 query detection scenario."""
        await self.monitor.start_monitoring()

        # Simulate N+1 pattern: get posts, then get comments for each post
        async with self.monitor.monitor_query(QueryType.SELECT, "posts"):
            await asyncio.sleep(0.05)  # Get posts query

        # Simulate getting comments for each post (N+1 pattern)
        for _i in range(5):
            async with self.monitor.monitor_query(
                QueryType.SELECT,
                "comments",
                query_text="SELECT * FROM comments WHERE post_id = ?",
            ):
                await asyncio.sleep(0.02)

        # Wait for analytics to process
        await asyncio.sleep(0.1)

        # Check for detected patterns
        patterns = await self.monitor.get_query_patterns()
        n_plus_one_patterns = [p for p in patterns if p.pattern_type == "n_plus_one"]

        assert len(n_plus_one_patterns) >= 1

        # Check for alerts
        alerts = await self.monitor.get_performance_alerts(
            alert_type=AlertType.N_PLUS_ONE
        )
        assert len(alerts) >= 1

        await self.monitor.stop_monitoring()

    @pytest.mark.asyncio
    async def test_performance_degradation_scenario(self):
        """Test performance degradation detection."""
        await self.monitor.start_monitoring()

        # Execute normal queries
        for _i in range(5):
            async with self.monitor.monitor_query(QueryType.SELECT, "users"):
                await asyncio.sleep(0.05)  # Normal performance

        # Simulate performance degradation
        for _i in range(5):
            async with self.monitor.monitor_query(QueryType.SELECT, "users"):
                await asyncio.sleep(0.2)  # Degraded performance

        # Check performance metrics
        metrics = await self.monitor.get_performance_metrics()
        assert metrics.total_queries == 10
        assert metrics.slow_queries > 0

        await self.monitor.stop_monitoring()

    @pytest.mark.asyncio
    async def test_comprehensive_monitoring_scenario(self):
        """Test comprehensive monitoring with various query types and patterns."""
        await self.monitor.start_monitoring()

        # Set up alert callback to capture alerts
        captured_alerts = []
        self.monitor.add_alert_callback(lambda alert: captured_alerts.append(alert))

        # Execute various types of queries
        query_scenarios = [
            # Normal queries
            {"type": QueryType.SELECT, "table": "users", "duration": 0.05},
            {"type": QueryType.INSERT, "table": "posts", "duration": 0.08},
            {"type": QueryType.UPDATE, "table": "users", "duration": 0.06},
            # Slow queries (should trigger alerts)
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
                user_id="test_user",
            )

            await asyncio.sleep(scenario["duration"])

            await self.monitor.finish_query(
                query_id=query_id,
                status=scenario.get("status", QueryStatus.SUCCESS),
                error_message="Test error"
                if scenario.get("status") == QueryStatus.ERROR
                else None,
            )

        # Wait for processing
        await asyncio.sleep(0.1)

        # Verify comprehensive tracking
        status = await self.monitor.get_monitoring_status()
        assert status["statistics"]["total_tracked_queries"] == len(query_scenarios)

        # Verify metrics calculation
        metrics = await self.monitor.get_performance_metrics()
        assert metrics.total_queries == len(query_scenarios)
        assert metrics.failed_queries == 1
        assert metrics.slow_queries >= 2  # The slow queries

        # Verify alerts were generated
        assert len(captured_alerts) > 0
        slow_alerts = [
            a for a in captured_alerts if a.alert_type == AlertType.SLOW_QUERY
        ]
        assert len(slow_alerts) >= 2

        await self.monitor.stop_monitoring()
