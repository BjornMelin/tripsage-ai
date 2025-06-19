"""
Advanced pytest configuration for DatabaseService testing.

This module provides comprehensive fixtures and utilities for testing the consolidated
DatabaseService with multi-layer test architecture supporting:
- Unit tests with property-based testing (Hypothesis)
- Integration tests with real database scenarios
- Performance benchmarks with pytest-benchmark
- Async testing patterns with proper connection management
- Advanced mocking and service factories
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock
from uuid import uuid4

import pytest
import pytest_asyncio
from hypothesis import strategies as st
from pydantic import SecretStr
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from tripsage_core.config import Settings
from tripsage_core.services.infrastructure.database_service import (
    ConnectionStats,
    DatabaseConfig,
    DatabaseMonitoringConfig,
    DatabasePerformanceConfig,
    DatabasePoolConfig,
    DatabaseSecurityConfig,
    DatabaseService,
    QueryMetrics,
    QueryType,
    SecurityAlert,
    SecurityEvent,
)

# Configure logging for test debugging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


# ============================================================================
# Configuration Strategies for Property-Based Testing
# ============================================================================


@st.composite
def valid_database_configs(draw):
    """Generate valid DatabaseConfig instances for property-based testing."""
    rate_limit_requests = draw(st.integers(min_value=10, max_value=10000))
    rate_limit_burst = draw(st.integers(min_value=rate_limit_requests, max_value=20000))

    pool_config = DatabasePoolConfig(
        pool_size=draw(st.integers(min_value=1, max_value=200)),
        max_overflow=draw(st.integers(min_value=0, max_value=1000)),
        pool_use_lifo=draw(st.booleans()),
        pool_pre_ping=draw(st.booleans()),
        pool_recycle=draw(st.integers(min_value=300, max_value=7200)),
        pool_timeout=draw(st.floats(min_value=1.0, max_value=120.0)),
    )

    monitoring_config = DatabaseMonitoringConfig(
        enable_monitoring=draw(st.booleans()),
        enable_metrics=draw(st.booleans()),
        enable_query_tracking=draw(st.booleans()),
        slow_query_threshold=draw(st.floats(min_value=0.1, max_value=10.0)),
    )

    security_config = DatabaseSecurityConfig(
        enable_security=draw(st.booleans()),
        enable_rate_limiting=draw(st.booleans()),
        enable_audit_logging=draw(st.booleans()),
        rate_limit_requests=rate_limit_requests,
        rate_limit_burst=rate_limit_burst,
    )

    performance_config = DatabasePerformanceConfig(
        enable_read_replicas=draw(st.booleans()),
        enable_circuit_breaker=draw(st.booleans()),
        circuit_breaker_threshold=draw(st.integers(min_value=1, max_value=20)),
        circuit_breaker_timeout=draw(st.floats(min_value=10.0, max_value=300.0)),
    )

    return DatabaseConfig(
        pool=pool_config,
        monitoring=monitoring_config,
        security=security_config,
        performance=performance_config,
    )


@st.composite
def edge_case_database_configs(draw):
    """Generate edge case DatabaseConfig instances for stress testing."""
    rate_limit_requests = draw(st.sampled_from([1, 5, 50000]))
    rate_limit_burst = max(rate_limit_requests, draw(st.sampled_from([1, 10, 100000])))

    pool_config = DatabasePoolConfig(
        pool_size=draw(st.sampled_from([1, 2, 500, 1000])),  # Extreme values
        max_overflow=draw(
            st.sampled_from([0, 1, 2000])
        ),  # Keep within validation limits
        pool_timeout=draw(st.sampled_from([0.1, 0.5, 300.0])),
    )

    monitoring_config = DatabaseMonitoringConfig(
        slow_query_threshold=draw(st.sampled_from([0.001, 0.01, 30.0]))
    )

    security_config = DatabaseSecurityConfig(
        rate_limit_requests=rate_limit_requests, rate_limit_burst=rate_limit_burst
    )

    performance_config = DatabasePerformanceConfig(
        circuit_breaker_threshold=draw(st.sampled_from([1, 2, 100]))
    )

    return DatabaseConfig(
        pool=pool_config,
        monitoring=monitoring_config,
        security=security_config,
        performance=performance_config,
    )


@st.composite
def query_data_strategies(draw):
    """Generate realistic query data for testing."""
    table_names = ["users", "trips", "flights", "accommodations", "chat_messages"]
    return {
        "table": draw(st.sampled_from(table_names)),
        "data": draw(
            st.dictionaries(
                keys=st.text(
                    min_size=1,
                    max_size=20,
                    alphabet=st.characters(whitelist_categories=["L"]),
                ),
                values=st.one_of(
                    st.text(min_size=1, max_size=100),
                    st.integers(min_value=1, max_value=100000),
                    st.floats(min_value=0.01, max_value=99999.99),
                    st.booleans(),
                    st.none(),
                ),
                min_size=1,
                max_size=10,
            )
        ),
        "filters": draw(
            st.dictionaries(
                keys=st.text(
                    min_size=1,
                    max_size=20,
                    alphabet=st.characters(whitelist_categories=["L"]),
                ),
                values=st.one_of(
                    st.text(min_size=1, max_size=50),
                    st.integers(min_value=1, max_value=1000),
                    st.uuids().map(str),
                ),
                min_size=0,
                max_size=5,
            )
        ),
        "user_id": draw(st.one_of(st.none(), st.uuids().map(str))),
    }


# ============================================================================
# Service Factory Fixtures
# ============================================================================


@pytest.fixture
def mock_settings_factory():
    """Factory for creating mock settings with various configurations."""

    def _create_settings(**overrides):
        defaults = {
            "environment": "testing",
            "debug": True,
            "database_url": "https://test.supabase.com",
            "database_public_key": SecretStr("test-public-key"),
            "database_service_key": SecretStr("test-service-key"),
            "database_password": SecretStr("test-password"),
            "database_jwt_secret": SecretStr("test-jwt-secret"),
            "secret_key": SecretStr("test-secret-key"),
            "redis_url": "redis://localhost:6379/1",
            "redis_password": "test-redis-password",
            "openai_api_key": SecretStr("sk-test-1234567890"),
            "weather_api_key": SecretStr("test-weather-key"),
            "google_maps_api_key": SecretStr("test-maps-key"),
            "duffel_api_key": SecretStr("test-duffel-key"),
        }

        settings_data = {**defaults, **overrides}
        settings = MagicMock(spec=Settings)

        for key, value in settings_data.items():
            setattr(settings, key, value)

        return settings

    return _create_settings


@pytest.fixture
def database_service_factory(mock_settings_factory):
    """Factory for creating DatabaseService instances with various configurations."""
    created_services: List[DatabaseService] = []

    def _create_service(config: Optional[DatabaseConfig] = None, **legacy_overrides):
        settings = mock_settings_factory()

        if config is None:
            # If no config provided but legacy overrides exist, create config from
            # legacy parameters
            if legacy_overrides:
                # Map legacy parameters to new config structure
                pool_config = DatabasePoolConfig(
                    pool_size=legacy_overrides.get("pool_size", 100),
                    max_overflow=legacy_overrides.get("max_overflow", 500),
                    pool_use_lifo=legacy_overrides.get("pool_use_lifo", True),
                    pool_pre_ping=legacy_overrides.get("pool_pre_ping", True),
                    pool_recycle=legacy_overrides.get("pool_recycle", 3600),
                    pool_timeout=legacy_overrides.get("pool_timeout", 30.0),
                )

                monitoring_config = DatabaseMonitoringConfig(
                    enable_monitoring=legacy_overrides.get("enable_monitoring", True),
                    enable_metrics=legacy_overrides.get("enable_metrics", True),
                    enable_query_tracking=legacy_overrides.get(
                        "enable_query_tracking", True
                    ),
                    slow_query_threshold=legacy_overrides.get(
                        "slow_query_threshold", 1.0
                    ),
                )

                security_config = DatabaseSecurityConfig(
                    enable_security=legacy_overrides.get("enable_security", True),
                    enable_rate_limiting=legacy_overrides.get(
                        "enable_rate_limiting", True
                    ),
                    enable_audit_logging=legacy_overrides.get(
                        "enable_audit_logging", True
                    ),
                    rate_limit_requests=legacy_overrides.get(
                        "rate_limit_requests", 1000
                    ),
                    rate_limit_burst=legacy_overrides.get("rate_limit_burst", 2000),
                )

                performance_config = DatabasePerformanceConfig(
                    enable_read_replicas=legacy_overrides.get(
                        "enable_read_replicas", True
                    ),
                    enable_circuit_breaker=legacy_overrides.get(
                        "enable_circuit_breaker", True
                    ),
                    circuit_breaker_threshold=legacy_overrides.get(
                        "circuit_breaker_threshold", 5
                    ),
                    circuit_breaker_timeout=legacy_overrides.get(
                        "circuit_breaker_timeout", 60.0
                    ),
                )

                config = DatabaseConfig(
                    pool=pool_config,
                    monitoring=monitoring_config,
                    security=security_config,
                    performance=performance_config,
                )
            else:
                config = DatabaseConfig.create_default()

        service = DatabaseService(settings=settings, config=config)
        created_services.append(service)
        return service

    yield _create_service

    # Cleanup all created services
    async def cleanup():
        for service in created_services:
            if service.is_connected:
                await service.close()

    if created_services:
        # Run cleanup in event loop if available
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Create a task for cleanup
                asyncio.create_task(cleanup())
            else:
                loop.run_until_complete(cleanup())
        except RuntimeError:
            # No event loop, create one
            asyncio.run(cleanup())


@pytest_asyncio.fixture
async def mock_database_service():
    """Create a fully mocked DatabaseService for unit testing."""
    service = AsyncMock(spec=DatabaseService)

    # Mock basic properties
    service.is_connected = True
    service.settings = MagicMock()

    # Mock connection stats
    service.get_connection_stats.return_value = ConnectionStats(
        active_connections=5,
        idle_connections=95,
        total_connections=100,
        pool_size=100,
        max_overflow=500,
        connection_errors=0,
        uptime_seconds=3600,
        queries_executed=1000,
        avg_query_time_ms=15.5,
        pool_utilization=5.0,
    )

    # Mock CRUD operations
    service.insert.return_value = [{"id": str(uuid4())}]
    service.select.return_value = []
    service.update.return_value = [{"id": str(uuid4())}]
    service.delete.return_value = [{"id": str(uuid4())}]
    service.upsert.return_value = [{"id": str(uuid4())}]
    service.count.return_value = 0

    # Mock vector search
    service.vector_search.return_value = []

    # Mock health check
    service.health_check.return_value = True

    # Mock metrics
    service.get_recent_queries.return_value = []
    service.get_security_alerts.return_value = []

    return service


@pytest_asyncio.fixture
async def in_memory_database_service():
    """Create a DatabaseService with in-memory SQLite for integration testing."""
    # Create in-memory SQLite engine for testing
    engine = create_engine(
        "sqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    # Create mock settings
    settings = MagicMock(spec=Settings)
    settings.environment = "testing"
    settings.database_url = "sqlite:///:memory:"
    settings.database_public_key = SecretStr("test-key")
    settings.database_service_key = SecretStr("test-service-key")
    settings.database_password = SecretStr("test-password")
    settings.database_jwt_secret = SecretStr("test-jwt")
    settings.secret_key = SecretStr("test-secret")

    # Create service with minimal configuration for testing
    test_config = DatabaseConfig(
        pool=DatabasePoolConfig(pool_size=5, max_overflow=10),
        monitoring=DatabaseMonitoringConfig(
            enable_monitoring=True,
            enable_metrics=False,  # Disable Prometheus to avoid import issues
        ),
        security=DatabaseSecurityConfig(enable_security=True),
        performance=DatabasePerformanceConfig(),
    )

    service = DatabaseService(settings=settings, config=test_config)

    # Mock the SQLAlchemy engine
    service._sqlalchemy_engine = engine

    # Mock Supabase client
    mock_client = AsyncMock()
    mock_table = AsyncMock()
    mock_table.select.return_value = mock_table
    mock_table.insert.return_value = mock_table
    mock_table.update.return_value = mock_table
    mock_table.delete.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.execute.return_value = Mock(data=[], count=0)
    mock_client.table.return_value = mock_table
    service._supabase_client = mock_client
    service._connected = True

    yield service

    # Cleanup
    if service._sqlalchemy_engine:
        service._sqlalchemy_engine.dispose()


# ============================================================================
# Test Data Factories
# ============================================================================


@pytest.fixture
def query_metrics_factory():
    """Factory for creating QueryMetrics test data."""

    def _create_metrics(count: int = 5, **overrides) -> List[QueryMetrics]:
        metrics = []
        for i in range(count):
            defaults = {
                "query_type": QueryType.SELECT,
                "table": f"test_table_{i}",
                "duration_ms": 10.0 + (i * 5.0),
                "rows_affected": i,
                "success": True,
                "user_id": str(uuid4()),
            }
            metric_data = {**defaults, **overrides}
            metrics.append(QueryMetrics(**metric_data))
        return metrics

    return _create_metrics


@pytest.fixture
def security_alert_factory():
    """Factory for creating SecurityAlert test data."""

    def _create_alerts(count: int = 3, **overrides) -> List[SecurityAlert]:
        alerts = []
        for i in range(count):
            defaults = {
                "event_type": SecurityEvent.SLOW_QUERY_DETECTED,
                "severity": "low",
                "message": f"Test alert {i}",
                "details": {"test": f"details_{i}"},
                "user_id": str(uuid4()),
            }
            alert_data = {**defaults, **overrides}
            alerts.append(SecurityAlert(**alert_data))
        return alerts

    return _create_alerts


# ============================================================================
# Performance Testing Fixtures
# ============================================================================


@pytest.fixture
def benchmark_config():
    """Configuration for performance benchmarks."""
    return {
        "min_rounds": 5,
        "max_time": 1.0,
        "warmup": True,
        "warmup_iterations": 2,
        "disable_gc": True,
        "sort": "mean",
    }


@pytest_asyncio.fixture
async def load_test_data():
    """Generate data for load testing scenarios."""
    users = [{"id": str(uuid4()), "email": f"user{i}@test.com"} for i in range(100)]
    trips = [
        {
            "id": str(uuid4()),
            "user_id": users[i % len(users)]["id"],
            "name": f"Trip {i}",
            "destination": f"City {i}",
        }
        for i in range(500)
    ]

    return {
        "users": users,
        "trips": trips,
        "query_vectors": [
            [0.1 * i] * 1536 for i in range(50)
        ],  # For vector search tests
    }


# ============================================================================
# Async Testing Utilities
# ============================================================================


@pytest_asyncio.fixture
async def async_context_manager():
    """Utility for testing async context managers."""

    @asynccontextmanager
    async def _test_context(service: DatabaseService, operation: str):
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            logger.debug(f"Operation {operation} took {duration:.3f}s")

    return _test_context


@pytest.fixture
def connection_lifecycle_tester():
    """Utility for testing connection lifecycle scenarios."""

    async def _test_lifecycle(service: DatabaseService, scenario: str = "normal"):
        """Test various connection lifecycle scenarios."""
        if scenario == "normal":
            await service.connect()
            assert service.is_connected
            await service.close()
            assert not service.is_connected

        elif scenario == "double_connect":
            await service.connect()
            await service.connect()  # Should be idempotent
            assert service.is_connected
            await service.close()

        elif scenario == "close_without_connect":
            await service.close()  # Should not raise error
            assert not service.is_connected

        elif scenario == "multiple_close":
            await service.connect()
            await service.close()
            await service.close()  # Should be idempotent
            assert not service.is_connected

    return _test_lifecycle


# ============================================================================
# Error Injection and Chaos Testing
# ============================================================================


@pytest.fixture
def error_injector():
    """Utility for injecting various types of errors during testing."""

    def _inject_errors(service: DatabaseService, error_type: str):
        """Inject specific types of errors for resilience testing."""
        if error_type == "connection_failure":
            service._supabase_client = None
            service._connected = False

        elif error_type == "slow_queries":
            original_monitor = service._monitor_query

            @asynccontextmanager
            async def slow_monitor(*args, **kwargs):
                async with original_monitor(*args, **kwargs) as query_id:
                    await asyncio.sleep(2.0)  # Simulate slow query
                    yield query_id

            service._monitor_query = slow_monitor

        elif error_type == "circuit_breaker_open":
            service._circuit_breaker_open = True
            service._circuit_breaker_failures = service.circuit_breaker_threshold

        elif error_type == "rate_limit_exceeded":
            # Fill rate limit window
            user_id = "test-user"
            service._rate_limit_window[user_id] = (
                service.rate_limit_requests + 1,
                time.time(),
            )

    return _inject_errors


# ============================================================================
# Stateful Testing Fixtures
# ============================================================================


@pytest.fixture
def stateful_test_runner():
    """Runner for stateful property-based testing scenarios."""

    class DatabaseServiceStateMachine:
        def __init__(self, service: DatabaseService):
            self.service = service
            self.connected = False
            self.tables_created = set()
            self.operations_count = 0

        async def connect(self):
            if not self.connected:
                await self.service.connect()
                self.connected = True

        async def disconnect(self):
            if self.connected:
                await self.service.close()
                self.connected = False

        async def insert_data(self, table: str, data: Dict[str, Any]):
            if self.connected:
                try:
                    await self.service.insert(table, data)
                    self.tables_created.add(table)
                    self.operations_count += 1
                except Exception as e:
                    logger.debug(f"Insert failed: {e}")

        async def query_data(self, table: str, filters: Dict[str, Any]):
            if self.connected and table in self.tables_created:
                try:
                    result = await self.service.select(table, filters=filters)
                    self.operations_count += 1
                    return result
                except Exception as e:
                    logger.debug(f"Query failed: {e}")
            return []

        def get_stats(self):
            return {
                "connected": self.connected,
                "tables_created": len(self.tables_created),
                "operations_count": self.operations_count,
            }

    return DatabaseServiceStateMachine


# ============================================================================
# Integration Testing Fixtures
# ============================================================================


@pytest_asyncio.fixture
async def real_database_service(monkeypatch):
    """Create a DatabaseService for integration testing with real connections.

    WARNING: This fixture requires real database credentials and should only
    be used for integration tests with appropriate test isolation.
    """
    # Only create if integration testing is explicitly enabled
    if not pytest.config.getoption("--run-integration", default=False):
        pytest.skip("Integration tests disabled - use --run-integration to enable")

    # Mock settings with real test database
    settings = MagicMock(spec=Settings)
    settings.environment = "integration_testing"
    settings.database_url = "https://test-integration.supabase.com"
    settings.database_public_key = SecretStr("integration-test-key")
    settings.database_service_key = SecretStr("integration-test-service-key")
    settings.database_password = SecretStr("integration-test-password")
    settings.database_jwt_secret = SecretStr("integration-test-jwt")
    settings.secret_key = SecretStr("integration-test-secret")

    # Create configuration for integration testing
    integration_config = DatabaseConfig(
        pool=DatabasePoolConfig(pool_size=5, max_overflow=10),
        monitoring=DatabaseMonitoringConfig(
            enable_monitoring=True,
            enable_metrics=False,  # Disable Prometheus for integration tests
        ),
        security=DatabaseSecurityConfig(enable_security=True),
        performance=DatabasePerformanceConfig(),
    )

    service = DatabaseService(settings=settings, config=integration_config)

    # Don't auto-connect - let tests control connection lifecycle
    yield service

    # Cleanup
    if service.is_connected:
        await service.close()


# ============================================================================
# Pytest Configuration Extensions
# ============================================================================


def pytest_configure(config):
    """Configure additional markers for database service testing."""
    config.addinivalue_line(
        "markers", "property: Property-based tests using Hypothesis"
    )
    config.addinivalue_line("markers", "performance: Performance benchmark tests")
    config.addinivalue_line(
        "markers", "integration: Integration tests with real database"
    )
    config.addinivalue_line("markers", "load: Load testing scenarios")
    config.addinivalue_line(
        "markers", "chaos: Chaos engineering and error injection tests"
    )
    config.addinivalue_line("markers", "stateful: Stateful property-based testing")


def pytest_addoption(parser):
    """Add command line options for database service testing."""
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run integration tests with real database connections",
    )
    parser.addoption(
        "--run-load-tests",
        action="store_true",
        default=False,
        help="Run load testing scenarios",
    )
    parser.addoption(
        "--benchmark-save",
        action="store",
        default=None,
        help="Save benchmark results to specified file",
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection based on command line options."""
    # Skip integration tests unless explicitly enabled
    if not config.getoption("--run-integration"):
        skip_integration = pytest.mark.skip(
            reason="need --run-integration option to run"
        )
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)

    # Skip load tests unless explicitly enabled
    if not config.getoption("--run-load-tests"):
        skip_load = pytest.mark.skip(reason="need --run-load-tests option to run")
        for item in items:
            if "load" in item.keywords:
                item.add_marker(skip_load)
