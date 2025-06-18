"""
Tests for database metrics collection functionality.

Tests cover Prometheus metrics collection, timing contexts,
and metrics aggregation for database operations.
"""

import time
from unittest.mock import patch

import pytest
from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram

from tripsage_core.monitoring.database_metrics import (
    DatabaseMetrics,
    get_database_metrics,
    reset_database_metrics,
)

class TestDatabaseMetrics:
    """Test suite for DatabaseMetrics class."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create isolated registry for testing
        self.registry = CollectorRegistry()
        self.metrics = DatabaseMetrics(registry=self.registry)

    def test_initialization(self):
        """Test metrics initialization."""
        assert self.metrics.registry == self.registry
        assert isinstance(self.metrics.connection_attempts, Counter)
        assert isinstance(self.metrics.connection_duration, Histogram)
        assert isinstance(self.metrics.active_connections, Gauge)
        assert isinstance(self.metrics.query_duration, Histogram)
        assert isinstance(self.metrics.query_total, Counter)
        assert isinstance(self.metrics.query_errors, Counter)
        assert isinstance(self.metrics.health_status, Gauge)

    def test_record_connection_attempt_success(self):
        """Test recording successful connection attempt."""
        self.metrics.record_connection_attempt("supabase", True, 0.5)

        # Check that metrics were recorded
        connection_metrics = self._get_metric_samples(self.metrics.connection_attempts)
        assert any(
            sample.labels.get("service") == "supabase"
            and sample.labels.get("status") == "success"
            for sample in connection_metrics
        )

    def test_record_connection_attempt_failure(self):
        """Test recording failed connection attempt."""
        self.metrics.record_connection_attempt("supabase", False, 1.0)

        # Check that failure was recorded
        connection_metrics = self._get_metric_samples(self.metrics.connection_attempts)
        assert any(
            sample.labels.get("service") == "supabase"
            and sample.labels.get("status") == "error"
            for sample in connection_metrics
        )

    def test_set_active_connections(self):
        """Test setting active connection count."""
        self.metrics.set_active_connections("supabase", 5)

        active_metrics = self._get_metric_samples(self.metrics.active_connections)
        supabase_sample = next(
            (s for s in active_metrics if s.labels.get("service") == "supabase"), None
        )
        assert supabase_sample is not None
        assert supabase_sample.value == 5

    def test_record_query_success(self):
        """Test recording successful query."""
        self.metrics.record_query("supabase", "SELECT", "users", 0.1, True)

        # Check query duration was recorded
        duration_metrics = self._get_metric_samples(self.metrics.query_duration)
        assert any(
            sample.labels.get("service") == "supabase"
            and sample.labels.get("operation") == "SELECT"
            and sample.labels.get("table") == "users"
            for sample in duration_metrics
        )

        # Check query total was incremented
        total_metrics = self._get_metric_samples(self.metrics.query_total)
        assert any(
            sample.labels.get("service") == "supabase"
            and sample.labels.get("operation") == "SELECT"
            and sample.labels.get("table") == "users"
            and sample.labels.get("status") == "success"
            for sample in total_metrics
        )

    def test_record_query_error(self):
        """Test recording query error."""
        self.metrics.record_query(
            "supabase", "INSERT", "users", 0.05, False, "ValueError"
        )

        # Check error was recorded
        error_metrics = self._get_metric_samples(self.metrics.query_errors)
        assert any(
            sample.labels.get("service") == "supabase"
            and sample.labels.get("operation") == "INSERT"
            and sample.labels.get("table") == "users"
            and sample.labels.get("error_type") == "ValueError"
            for sample in error_metrics
        )

    def test_time_query_context_manager_success(self):
        """Test query timing context manager with successful operation."""
        with self.metrics.time_query("supabase", "SELECT", "trips"):
            time.sleep(0.01)  # Simulate query time

        # Check that metrics were recorded
        duration_metrics = self._get_metric_samples(self.metrics.query_duration)
        assert any(
            sample.labels.get("service") == "supabase"
            and sample.labels.get("operation") == "SELECT"
            and sample.labels.get("table") == "trips"
            for sample in duration_metrics
        )

    def test_time_query_context_manager_error(self):
        """Test query timing context manager with error."""
        with pytest.raises(ValueError):
            with self.metrics.time_query("supabase", "DELETE", "trips"):
                raise ValueError("Test error")

        # Check that error was recorded
        error_metrics = self._get_metric_samples(self.metrics.query_errors)
        assert any(
            sample.labels.get("service") == "supabase"
            and sample.labels.get("operation") == "DELETE"
            and sample.labels.get("table") == "trips"
            and sample.labels.get("error_type") == "ValueError"
            for sample in error_metrics
        )

    def test_record_health_check(self):
        """Test recording health check results."""
        self.metrics.record_health_check("supabase", True)

        health_metrics = self._get_metric_samples(self.metrics.health_status)
        supabase_sample = next(
            (s for s in health_metrics if s.labels.get("service") == "supabase"), None
        )
        assert supabase_sample is not None
        assert supabase_sample.value == 1.0

        # Test unhealthy status
        self.metrics.record_health_check("supabase", False)

        health_metrics = self._get_metric_samples(self.metrics.health_status)
        supabase_sample = next(
            (s for s in health_metrics if s.labels.get("service") == "supabase"), None
        )
        assert supabase_sample is not None
        assert supabase_sample.value == 0.0

    def test_set_pool_metrics(self):
        """Test setting connection pool metrics."""
        self.metrics.set_pool_metrics("supabase", 20, 15)

        # Check pool size
        size_metrics = self._get_metric_samples(self.metrics.pool_size)
        supabase_size = next(
            (s for s in size_metrics if s.labels.get("service") == "supabase"), None
        )
        assert supabase_size is not None
        assert supabase_size.value == 20

        # Check available connections
        available_metrics = self._get_metric_samples(self.metrics.pool_available)
        supabase_available = next(
            (s for s in available_metrics if s.labels.get("service") == "supabase"),
            None,
        )
        assert supabase_available is not None
        assert supabase_available.value == 15

    def test_set_database_info(self):
        """Test setting database information."""
        self.metrics.set_database_info(
            "supabase",
            version="15.3",
            host="localhost",
            database="tripsage_test",
            extra_field="test_value",
        )

        # Database info is stored as Info metric
        info_metrics = self._get_metric_samples(self.metrics.database_info)
        assert len(info_metrics) > 0

    def test_time_transaction_context_manager(self):
        """Test transaction timing context manager."""
        with self.metrics.time_transaction("supabase"):
            time.sleep(0.01)  # Simulate transaction time

        # Check that transaction duration was recorded
        transaction_metrics = self._get_metric_samples(
            self.metrics.transaction_duration
        )
        assert any(
            sample.labels.get("service") == "supabase" for sample in transaction_metrics
        )

    def test_get_metrics_summary(self):
        """Test getting metrics summary."""
        # Record some metrics
        self.metrics.record_connection_attempt("supabase", True, 0.5)
        self.metrics.set_active_connections("supabase", 3)
        self.metrics.record_query("supabase", "SELECT", "users", 0.1, True)
        self.metrics.record_health_check("supabase", True)

        summary = self.metrics.get_metrics_summary()

        assert "connection_attempts" in summary
        assert "active_connections" in summary
        assert "query_total" in summary
        assert "query_errors" in summary
        assert "health_status" in summary

    @patch("tripsage_core.monitoring.database_metrics.start_http_server")
    def test_start_metrics_server(self, mock_start_server):
        """Test starting metrics server."""
        self.metrics.start_metrics_server(8001)

        mock_start_server.assert_called_once_with(8001, registry=self.registry)

    @patch("tripsage_core.monitoring.database_metrics.start_http_server")
    def test_start_metrics_server_error(self, mock_start_server):
        """Test metrics server startup error handling."""
        mock_start_server.side_effect = Exception("Port already in use")

        with pytest.raises(Exception, match="Port already in use"):
            self.metrics.start_metrics_server(8000)

    def _get_metric_samples(self, metric):
        """Helper method to get metric samples."""
        try:
            metric_families = list(metric.collect())
            if metric_families:
                return metric_families[0].samples
        except (IndexError, AttributeError):
            pass
        return []

class TestGlobalMetricsInstance:
    """Test global metrics instance management."""

    def setup_method(self):
        """Reset global state before each test."""
        reset_database_metrics()

    def teardown_method(self):
        """Reset global state after each test."""
        reset_database_metrics()

    def test_get_database_metrics_singleton(self):
        """Test that get_database_metrics returns singleton."""
        metrics1 = get_database_metrics()
        metrics2 = get_database_metrics()

        assert metrics1 is metrics2
        assert isinstance(metrics1, DatabaseMetrics)

    def test_reset_database_metrics(self):
        """Test resetting global metrics instance."""
        metrics1 = get_database_metrics()
        reset_database_metrics()
        metrics2 = get_database_metrics()

        assert metrics1 is not metrics2

class TestMetricsIntegration:
    """Integration tests for metrics collection."""

    def setup_method(self):
        """Set up test fixtures."""
        self.registry = CollectorRegistry()
        self.metrics = DatabaseMetrics(registry=self.registry)

    def test_complete_operation_flow(self):
        """Test complete database operation flow with metrics."""
        # Simulate connection
        self.metrics.record_connection_attempt("supabase", True, 0.5)
        self.metrics.set_active_connections("supabase", 1)

        # Simulate queries
        with self.metrics.time_query("supabase", "SELECT", "users"):
            time.sleep(0.001)

        with self.metrics.time_query("supabase", "INSERT", "trips"):
            time.sleep(0.002)

        # Simulate transaction
        with self.metrics.time_transaction("supabase"):
            time.sleep(0.001)

        # Check health
        self.metrics.record_health_check("supabase", True)

        # Verify metrics were collected
        summary = self.metrics.get_metrics_summary()
        assert len(summary["connection_attempts"]) > 0
        assert len(summary["active_connections"]) > 0
        assert len(summary["query_total"]) > 0
        assert len(summary["health_status"]) > 0

    def test_error_handling_flow(self):
        """Test error handling in metrics collection."""
        # Simulate connection failure
        self.metrics.record_connection_attempt("supabase", False, 2.0)

        # Simulate query error
        self.metrics.record_query(
            "supabase", "UPDATE", "users", 0.1, False, "TimeoutError"
        )

        # Check unhealthy status
        self.metrics.record_health_check("supabase", False)

        # Verify error metrics
        summary = self.metrics.get_metrics_summary()
        assert len(summary["query_errors"]) > 0

        # Check that health status is 0 (unhealthy)
        health_status = summary["health_status"]
        supabase_health = next(
            (v for k, v in health_status.items() if "supabase" in k), None
        )
        assert supabase_health == 0.0

    def test_concurrent_metrics_collection(self):
        """Test metrics collection under concurrent access."""
        import threading

        def worker():
            for i in range(10):
                self.metrics.record_query("supabase", "SELECT", "users", 0.01, True)
                self.metrics.set_active_connections("supabase", i)

        # Start multiple threads
        threads = [threading.Thread(target=worker) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Verify metrics were collected
        summary = self.metrics.get_metrics_summary()
        assert len(summary["query_total"]) > 0
        assert len(summary["active_connections"]) > 0
