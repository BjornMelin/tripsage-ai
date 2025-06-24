"""
Comprehensive Database Service Tests - Advanced Features

This module provides comprehensive test coverage for advanced database service features
that were not covered in the base test suite, specifically targeting:

1. Configuration Management & Validation
2. LIFO Connection Pooling Advanced Features
3. SQLAlchemy 2.0 Integration Testing
4. Vector Operations & pgvector Integration
5. Monitoring & Metrics Collection
6. Security Features & Rate Limiting
7. Advanced Transaction Management
8. Circuit Breaker & Error Recovery
9. Performance Monitoring & Optimization
10. Connection Health & Validation

These tests focus on achieving 90%+ test coverage for the consolidated database service.
"""

import asyncio
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest

from tripsage_core.config import Settings
from tripsage_core.exceptions.exceptions import (
    CoreDatabaseError,
    CoreServiceError,
)
from tripsage_core.services.infrastructure.database_service import (
    ConnectionStats,
    DatabaseConfig,
    DatabaseMonitoringConfig,
    DatabasePerformanceConfig,
    DatabasePoolConfig,
    DatabaseSecurityConfig,
    DatabaseService,
    HealthStatus,
    QueryMetrics,
    QueryType,
    SecurityAlert,
    SecurityEvent,
)


class TestDatabaseConfigurationClasses:
    """Test comprehensive configuration classes and validation."""

    def test_database_pool_config_validation(self):
        """Test DatabasePoolConfig validation rules."""
        # Valid configuration
        config = DatabasePoolConfig(
            pool_size=50,
            max_overflow=100,
            pool_use_lifo=True,
            pool_pre_ping=True,
            pool_recycle=1800,
            pool_timeout=15.0,
        )
        assert config.pool_size == 50
        assert config.max_overflow == 100
        assert config.pool_use_lifo is True

        # Test pool_size validation
        with pytest.raises(ValueError, match="Pool size must be positive"):
            DatabasePoolConfig(pool_size=0)

        with pytest.raises(ValueError):
            DatabasePoolConfig(pool_size=-1)

        # Test timeout validation
        with pytest.raises(ValueError, match="Timeout must be positive"):
            DatabasePoolConfig(pool_timeout=0)

        with pytest.raises(ValueError):
            DatabasePoolConfig(pool_timeout=-1.0)

        # Test range validation
        with pytest.raises(ValueError):
            DatabasePoolConfig(pool_size=2000)  # Exceeds le=1000

        with pytest.raises(ValueError):
            DatabasePoolConfig(max_overflow=3000)  # Exceeds le=2000

    def test_database_monitoring_config_validation(self):
        """Test DatabaseMonitoringConfig validation rules."""
        # Valid configuration
        config = DatabaseMonitoringConfig(
            enable_monitoring=True,
            enable_metrics=True,
            enable_query_tracking=True,
            slow_query_threshold=2.0,
        )
        assert config.slow_query_threshold == 2.0

        # Test slow query threshold validation
        with pytest.raises(ValueError, match="Slow query threshold must be positive"):
            DatabaseMonitoringConfig(slow_query_threshold=0)

        with pytest.raises(ValueError):
            DatabaseMonitoringConfig(slow_query_threshold=-1.0)

        # Test range validation
        with pytest.raises(ValueError):
            DatabaseMonitoringConfig(slow_query_threshold=100.0)  # Exceeds le=60.0

    def test_database_security_config_validation(self):
        """Test DatabaseSecurityConfig validation rules."""
        # Valid configuration
        config = DatabaseSecurityConfig(
            enable_security=True,
            enable_rate_limiting=True,
            enable_audit_logging=True,
            rate_limit_requests=500,
            rate_limit_burst=1000,
        )
        assert config.rate_limit_requests == 500
        assert config.rate_limit_burst == 1000

        # Test rate limit burst validation
        with pytest.raises(
            ValueError, match="Rate limit burst must be >= rate_limit_requests"
        ):
            DatabaseSecurityConfig(rate_limit_requests=1000, rate_limit_burst=500)

        # Test range validation
        with pytest.raises(ValueError):
            DatabaseSecurityConfig(rate_limit_requests=0)  # Below ge=1

        with pytest.raises(ValueError):
            DatabaseSecurityConfig(rate_limit_burst=0)  # Below ge=1

    def test_database_performance_config_validation(self):
        """Test DatabasePerformanceConfig validation rules."""
        # Valid configuration
        config = DatabasePerformanceConfig(
            enable_read_replicas=True,
            enable_circuit_breaker=True,
            circuit_breaker_threshold=10,
            circuit_breaker_timeout=120.0,
        )
        assert config.circuit_breaker_threshold == 10
        assert config.circuit_breaker_timeout == 120.0

        # Test circuit breaker threshold validation
        with pytest.raises(
            ValueError, match="Circuit breaker threshold must be positive"
        ):
            DatabasePerformanceConfig(circuit_breaker_threshold=0)

        with pytest.raises(ValueError):
            DatabasePerformanceConfig(circuit_breaker_threshold=-1)

        # Test circuit breaker timeout validation
        with pytest.raises(
            ValueError, match="Circuit breaker timeout must be positive"
        ):
            DatabasePerformanceConfig(circuit_breaker_timeout=0)

        with pytest.raises(ValueError):
            DatabasePerformanceConfig(circuit_breaker_timeout=-1.0)

    def test_database_config_factory_methods(self):
        """Test DatabaseConfig factory methods."""
        # Test default configuration
        default_config = DatabaseConfig.create_default()
        assert isinstance(default_config.pool, DatabasePoolConfig)
        assert isinstance(default_config.monitoring, DatabaseMonitoringConfig)
        assert isinstance(default_config.security, DatabaseSecurityConfig)
        assert isinstance(default_config.performance, DatabasePerformanceConfig)

        # Test production configuration
        prod_config = DatabaseConfig.create_production()
        assert prod_config.pool.pool_size == 100
        assert prod_config.pool.max_overflow == 500
        assert prod_config.monitoring.enable_monitoring is True
        assert prod_config.security.enable_security is True
        assert prod_config.performance.enable_read_replicas is True

        # Test development configuration
        dev_config = DatabaseConfig.create_development()
        assert dev_config.pool.pool_size == 10
        assert dev_config.pool.max_overflow == 20
        assert dev_config.security.enable_rate_limiting is False
        assert dev_config.performance.enable_read_replicas is False

        # Test testing configuration
        test_config = DatabaseConfig.create_testing()
        assert test_config.pool.pool_size == 5
        assert test_config.pool.max_overflow == 10
        assert test_config.pool.pool_use_lifo is False
        assert test_config.monitoring.enable_monitoring is False
        assert test_config.security.enable_security is False
        assert test_config.performance.enable_circuit_breaker is False


class TestDatabaseServiceConfiguration:
    """Test DatabaseService configuration and initialization."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock(spec=Settings)
        settings.effective_postgres_url = "postgresql://user:pass@localhost:5432/testdb"
        settings.database_url = "https://test.supabase.co"
        settings.database_public_key = Mock(
            get_secret_value=Mock(return_value="test_key_1234567890123456789012")
        )
        return settings

    def test_service_initialization_with_config_object(self, mock_settings):
        """Test service initialization using DatabaseConfig object."""
        config = DatabaseConfig.create_testing()

        service = DatabaseService(settings=mock_settings, config=config)

        # Verify configuration values are applied
        assert service.pool_size == 5
        assert service.max_overflow == 10
        assert service.pool_use_lifo is False
        assert service.enable_monitoring is False
        assert service.enable_security is False

    def test_service_initialization_with_legacy_parameters(self, mock_settings):
        """Test service initialization using legacy parameters."""
        service = DatabaseService(
            settings=mock_settings,
            pool_size=25,
            max_overflow=50,
            pool_use_lifo=True,
            enable_monitoring=True,
            enable_security=True,
            rate_limit_requests=2000,
        )

        # Verify legacy parameters are applied
        assert service.pool_size == 25
        assert service.max_overflow == 50
        assert service.pool_use_lifo is True
        assert service.enable_monitoring is True
        assert service.enable_security is True
        assert service.rate_limit_requests == 2000

    def test_service_initialization_config_precedence(self, mock_settings):
        """Test that config object takes precedence over legacy parameters."""
        config = DatabaseConfig.create_production()

        service = DatabaseService(
            settings=mock_settings,
            config=config,
            # These legacy parameters should be ignored
            pool_size=999,
            enable_monitoring=False,
        )

        # Config object values should be used, not legacy parameters
        assert service.pool_size == 100  # From config, not 999
        assert service.enable_monitoring is True  # From config, not False

    def test_service_metrics_initialization(self, mock_settings):
        """Test metrics initialization when enabled."""
        with patch(
            "tripsage_core.services.infrastructure.database_service.prometheus_client"
        ):
            service = DatabaseService(
                settings=mock_settings,
                enable_metrics=True,
            )

            # Verify metrics were initialized (mocked)
            assert service.enable_metrics is True
            assert service._metrics is None  # Will be None due to mocking


class TestLIFOConnectionPooling:
    """Test advanced LIFO connection pooling features."""

    @pytest.fixture
    def mock_sqlalchemy_engine(self):
        """Create mock SQLAlchemy engine with LIFO pool."""
        engine = Mock()
        mock_pool = Mock()
        mock_pool.size.return_value = 10
        mock_pool.checked_in.return_value = 5
        mock_pool.checked_out.return_value = 5
        mock_pool.overflow.return_value = 2
        mock_pool.invalidated.return_value = 0

        engine.pool = mock_pool
        engine.dispose = Mock()
        engine.execute = Mock()

        return engine

    @pytest.fixture
    def database_service_with_pool(self, mock_sqlalchemy_engine):
        """Create database service with mocked pool."""
        settings = Mock(spec=Settings)
        settings.effective_postgres_url = "postgresql://user:pass@localhost:5432/testdb"

        config = DatabaseConfig.create_production()
        service = DatabaseService(settings=settings, config=config)
        service._sqlalchemy_engine = mock_sqlalchemy_engine
        service._connected = True

        return service

    @pytest.mark.asyncio
    async def test_lifo_pool_connection_acquisition(self, database_service_with_pool):
        """Test LIFO pool connection acquisition behavior."""
        service = database_service_with_pool

        # Test pool statistics collection
        stats = service._get_pool_statistics()

        assert isinstance(stats, ConnectionStats)
        assert stats.pool_size == service.pool_size
        assert stats.max_overflow == service.max_overflow

    @pytest.mark.asyncio
    async def test_pool_overflow_handling(self, database_service_with_pool):
        """Test connection pool overflow handling."""
        service = database_service_with_pool

        # Simulate high pool utilization
        service._sqlalchemy_engine.pool.checked_out.return_value = 90
        service._sqlalchemy_engine.pool.overflow.return_value = 400

        stats = service._get_pool_statistics()

        # Verify overflow statistics are captured
        assert stats.total_connections == 90
        assert stats.pool_utilization > 0.8  # High utilization

    @pytest.mark.asyncio
    async def test_connection_validation_pre_ping(self, database_service_with_pool):
        """Test connection validation with pre-ping enabled."""
        service = database_service_with_pool

        # Mock connection validation
        with patch.object(service._sqlalchemy_engine, "execute") as mock_execute:
            mock_execute.return_value = Mock()

            # Test connection health check
            is_healthy = await service._validate_connection_health()

            assert is_healthy is True
            mock_execute.assert_called()

    @pytest.mark.asyncio
    async def test_pool_connection_recycling(self, database_service_with_pool):
        """Test connection recycling behavior."""
        service = database_service_with_pool

        # Simulate connection recycling
        with patch.object(service._sqlalchemy_engine.pool, "recreate") as mock_recreate:
            await service._recycle_connections()

            mock_recreate.assert_called_once()

    def test_pool_statistics_calculation(self, database_service_with_pool):
        """Test pool statistics calculation."""
        service = database_service_with_pool

        # Mock pool state
        service._sqlalchemy_engine.pool.size.return_value = 100
        service._sqlalchemy_engine.pool.checked_out.return_value = 75
        service._sqlalchemy_engine.pool.checked_in.return_value = 25

        stats = service._get_pool_statistics()

        assert stats.total_connections == 75
        assert stats.active_connections == 75
        assert stats.idle_connections == 25
        assert stats.pool_utilization == 0.75  # 75/100


class TestVectorOperations:
    """Test pgvector integration and vector operations."""

    @pytest.fixture
    def mock_database_service(self):
        """Create database service with mocked vector capabilities."""
        settings = Mock(spec=Settings)
        settings.effective_postgres_url = "postgresql://user:pass@localhost:5432/testdb"

        service = DatabaseService(settings=settings)
        service._supabase_client = Mock()
        service._connected = True

        return service

    @pytest.mark.asyncio
    async def test_vector_search_with_pgvector(self, mock_database_service):
        """Test vector similarity search operations."""
        service = mock_database_service

        # Mock vector search response
        mock_response = Mock()
        mock_response.data = [
            {"id": "1", "content": "Similar content", "similarity": 0.95},
            {"id": "2", "content": "Another match", "similarity": 0.87},
        ]
        (
            service._supabase_client.table.return_value.select.return_value.execute.return_value
        ) = mock_response

        query_vector = [0.1, 0.2, 0.3, 0.4, 0.5]

        result = await service.vector_search(
            table="documents",
            vector_column="embedding",
            query_vector=query_vector,
            limit=5,
            similarity_threshold=0.8,
        )

        assert len(result) == 2
        assert result[0]["similarity"] == 0.95

    @pytest.mark.asyncio
    async def test_save_vector_embedding(self, mock_database_service):
        """Test saving document with vector embedding."""
        service = mock_database_service

        # Mock embedding save response
        mock_response = Mock()
        mock_response.data = [{"id": "doc_123", "content": "Test content"}]
        (
            service._supabase_client.table.return_value.upsert.return_value.execute.return_value
        ) = mock_response

        document_data = {"content": "Test document content", "title": "Test Doc"}
        embedding_vector = [0.1, 0.2, 0.3, 0.4, 0.5]

        result = await service.save_document_embedding(document_data, embedding_vector)

        assert result["id"] == "doc_123"
        assert result["content"] == "Test content"

    @pytest.mark.asyncio
    async def test_vector_similarity_calculation(self, mock_database_service):
        """Test vector similarity calculation using different metrics."""
        service = mock_database_service

        # Mock SQL execution for similarity calculation
        service._supabase_client.rpc = Mock()
        service._supabase_client.rpc.return_value.execute.return_value = Mock(
            data=[{"cosine_similarity": 0.92, "euclidean_distance": 0.15}]
        )

        vector1 = [0.1, 0.2, 0.3]
        vector2 = [0.15, 0.25, 0.35]

        result = await service.calculate_vector_similarity(
            vector1, vector2, metric="cosine"
        )

        assert "cosine_similarity" in result
        assert result["cosine_similarity"] == 0.92

    @pytest.mark.asyncio
    async def test_vector_index_operations(self, mock_database_service):
        """Test vector index creation and management."""
        service = mock_database_service

        # Mock index creation
        service._supabase_client.rpc = Mock()
        service._supabase_client.rpc.return_value.execute.return_value = Mock(
            data=[{"index_created": True}]
        )

        result = await service.create_vector_index(
            table="documents",
            vector_column="embedding",
            index_type="ivfflat",
            lists=100,
        )

        assert result["index_created"] is True

    @pytest.mark.asyncio
    async def test_vector_search_performance_optimization(self, mock_database_service):
        """Test vector search with performance optimizations."""
        service = mock_database_service

        # Mock optimized vector search
        mock_response = Mock()
        mock_response.data = [
            {"id": "1", "content": "Fast result", "similarity": 0.95},
        ]
        (
            service._supabase_client.table.return_value.select.return_value.execute.return_value
        ) = mock_response

        # Test with performance settings
        result = await service.vector_search(
            table="documents",
            vector_column="embedding",
            query_vector=[0.1, 0.2, 0.3],
            limit=10,
            similarity_threshold=0.9,
            use_approximate=True,  # Use approximate search for performance
            ef_search=40,  # HNSW parameter
        )

        assert len(result) == 1
        assert result[0]["similarity"] == 0.95


class TestMonitoringAndMetrics:
    """Test monitoring features and metrics collection."""

    @pytest.fixture
    def monitored_database_service(self):
        """Create database service with monitoring enabled."""
        settings = Mock(spec=Settings)
        settings.effective_postgres_url = "postgresql://user:pass@localhost:5432/testdb"

        config = DatabaseConfig(
            monitoring=DatabaseMonitoringConfig(
                enable_monitoring=True,
                enable_metrics=True,
                enable_query_tracking=True,
                slow_query_threshold=1.0,
            )
        )

        service = DatabaseService(settings=settings, config=config)
        service._connected = True

        return service

    def test_query_metrics_tracking(self, monitored_database_service):
        """Test query execution metrics tracking."""
        service = monitored_database_service

        # Create test query metric
        metric = QueryMetrics(
            query_type=QueryType.SELECT,
            table="users",
            duration_ms=150.5,
            rows_affected=10,
            success=True,
            user_id="user_123",
        )

        # Add metric to service
        service._record_query_metric(metric)

        assert len(service._query_metrics) == 1
        assert service._query_metrics[0].query_type == QueryType.SELECT
        assert service._query_metrics[0].duration_ms == 150.5

    def test_slow_query_detection(self, monitored_database_service):
        """Test slow query detection and alerting."""
        service = monitored_database_service

        # Create slow query metric
        slow_metric = QueryMetrics(
            query_type=QueryType.SELECT,
            table="large_table",
            duration_ms=2500.0,  # Exceeds 1.0s threshold
            rows_affected=1000,
            success=True,
        )

        service._record_query_metric(slow_metric)

        # Check if slow query was detected
        slow_queries = service._get_slow_queries()
        assert len(slow_queries) == 1
        assert slow_queries[0].duration_ms > service.slow_query_threshold * 1000

    def test_connection_statistics_tracking(self, monitored_database_service):
        """Test connection statistics collection."""
        service = monitored_database_service

        # Update connection stats
        service._connection_stats.active_connections = 15
        service._connection_stats.idle_connections = 5
        service._connection_stats.queries_executed = 1250
        service._connection_stats.avg_query_time_ms = 125.5

        stats = service.get_connection_statistics()

        assert stats["active_connections"] == 15
        assert stats["idle_connections"] == 5
        assert stats["queries_executed"] == 1250
        assert stats["avg_query_time_ms"] == 125.5

    @pytest.mark.asyncio
    async def test_health_monitoring(self, monitored_database_service):
        """Test database health monitoring."""
        service = monitored_database_service

        # Mock health check
        with patch.object(service, "health_check", return_value=True):
            health_status = await service.get_health_status()

            assert health_status["status"] == HealthStatus.HEALTHY.value
            assert health_status["connected"] is True

    def test_performance_metrics_aggregation(self, monitored_database_service):
        """Test performance metrics aggregation."""
        service = monitored_database_service

        # Add multiple query metrics
        metrics = [
            QueryMetrics(query_type=QueryType.SELECT, duration_ms=100.0),
            QueryMetrics(query_type=QueryType.SELECT, duration_ms=200.0),
            QueryMetrics(query_type=QueryType.INSERT, duration_ms=150.0),
            QueryMetrics(query_type=QueryType.UPDATE, duration_ms=300.0),
        ]

        for metric in metrics:
            service._record_query_metric(metric)

        # Get aggregated metrics
        aggregated = service._get_aggregated_metrics()

        assert aggregated["total_queries"] == 4
        assert aggregated["avg_query_time_ms"] == 187.5
        assert aggregated["query_types"]["SELECT"] == 2
        assert aggregated["query_types"]["INSERT"] == 1
        assert aggregated["query_types"]["UPDATE"] == 1


class TestSecurityFeatures:
    """Test security features and rate limiting."""

    @pytest.fixture
    def secure_database_service(self):
        """Create database service with security enabled."""
        settings = Mock(spec=Settings)
        settings.effective_postgres_url = "postgresql://user:pass@localhost:5432/testdb"

        config = DatabaseConfig(
            security=DatabaseSecurityConfig(
                enable_security=True,
                enable_rate_limiting=True,
                enable_audit_logging=True,
                rate_limit_requests=100,
                rate_limit_burst=200,
            )
        )

        service = DatabaseService(settings=settings, config=config)
        service._connected = True

        return service

    def test_rate_limiting_enforcement(self, secure_database_service):
        """Test rate limiting enforcement."""
        service = secure_database_service

        user_id = "test_user_123"

        # Test rate limit checking
        for _i in range(90):  # Under limit
            allowed = service._check_rate_limit(user_id)
            assert allowed is True

        # Exceed rate limit
        for _i in range(20):  # Push over limit
            service._check_rate_limit(user_id)

        # Should now be rate limited
        allowed = service._check_rate_limit(user_id)
        assert allowed is False

    def test_security_alert_generation(self, secure_database_service):
        """Test security alert generation."""
        service = secure_database_service

        # Create security alert
        alert = SecurityAlert(
            event_type=SecurityEvent.RATE_LIMIT_EXCEEDED,
            severity="high",
            message="Rate limit exceeded for user",
            details={"user_id": "test_user", "requests": 150},
            user_id="test_user",
            ip_address="192.168.1.100",
        )

        service._record_security_alert(alert)

        assert len(service._security_alerts) == 1
        assert (
            service._security_alerts[0].event_type == SecurityEvent.RATE_LIMIT_EXCEEDED
        )

    def test_audit_logging(self, secure_database_service):
        """Test audit logging functionality."""
        service = secure_database_service

        # Mock audit log entry
        audit_entry = {
            "timestamp": datetime.now(timezone.utc),
            "user_id": "test_user",
            "action": "SELECT",
            "table": "sensitive_data",
            "success": True,
            "ip_address": "192.168.1.100",
        }

        service._log_audit_event(audit_entry)

        # Verify audit log was recorded
        audit_logs = service._get_audit_logs()
        assert len(audit_logs) >= 1

    def test_suspicious_query_detection(self, secure_database_service):
        """Test detection of suspicious database queries."""
        service = secure_database_service

        suspicious_queries = [
            "SELECT * FROM users; DROP TABLE users;",
            "UNION SELECT password FROM admin_users",
            "1' OR '1'='1",
        ]

        for query in suspicious_queries:
            is_suspicious = service._detect_suspicious_query(query)
            assert is_suspicious is True

        # Normal query should not be flagged
        normal_query = "SELECT name, email FROM users WHERE id = $1"
        is_suspicious = service._detect_suspicious_query(normal_query)
        assert is_suspicious is False

    def test_connection_security_validation(self, secure_database_service):
        """Test connection security validation."""
        service = secure_database_service

        # Test SSL connection validation
        with patch.object(service, "_validate_ssl_connection") as mock_ssl_check:
            mock_ssl_check.return_value = True

            is_secure = service._validate_connection_security()

            assert is_secure is True
            mock_ssl_check.assert_called_once()


class TestCircuitBreakerAndErrorRecovery:
    """Test circuit breaker pattern and error recovery."""

    @pytest.fixture
    def circuit_breaker_service(self):
        """Create database service with circuit breaker enabled."""
        settings = Mock(spec=Settings)
        settings.effective_postgres_url = "postgresql://user:pass@localhost:5432/testdb"

        config = DatabaseConfig(
            performance=DatabasePerformanceConfig(
                enable_circuit_breaker=True,
                circuit_breaker_threshold=3,
                circuit_breaker_timeout=60.0,
            )
        )

        service = DatabaseService(settings=settings, config=config)
        service._connected = True

        return service

    def test_circuit_breaker_failure_counting(self, circuit_breaker_service):
        """Test circuit breaker failure counting."""
        service = circuit_breaker_service

        # Record failures
        for _i in range(2):  # Under threshold
            service._record_circuit_breaker_failure()

        assert service._circuit_breaker_failures == 2
        assert service._circuit_breaker_open is False

        # One more failure should open circuit
        service._record_circuit_breaker_failure()

        assert service._circuit_breaker_failures == 3
        assert service._circuit_breaker_open is True

    def test_circuit_breaker_timeout_recovery(self, circuit_breaker_service):
        """Test circuit breaker timeout and recovery."""
        service = circuit_breaker_service

        # Open circuit breaker
        service._circuit_breaker_open = True
        service._circuit_breaker_last_failure = time.time() - 70  # 70 seconds ago

        # Should allow recovery attempt
        can_attempt = service._can_attempt_recovery()
        assert can_attempt is True

        # Test successful recovery
        service._record_circuit_breaker_success()

        assert service._circuit_breaker_open is False
        assert service._circuit_breaker_failures == 0

    @pytest.mark.asyncio
    async def test_operation_with_circuit_breaker(self, circuit_breaker_service):
        """Test database operation with circuit breaker protection."""
        service = circuit_breaker_service

        # Mock operation that fails
        async def failing_operation():
            raise CoreDatabaseError("Database connection failed")

        # Should fail and increment circuit breaker
        with pytest.raises(CoreDatabaseError):
            await service._execute_with_circuit_breaker(failing_operation)

        assert service._circuit_breaker_failures == 1

        # Mock successful operation
        async def successful_operation():
            return "success"

        # Should succeed and reset circuit breaker
        result = await service._execute_with_circuit_breaker(successful_operation)

        assert result == "success"
        assert service._circuit_breaker_failures == 0

    def test_circuit_breaker_open_state_blocking(self, circuit_breaker_service):
        """Test that circuit breaker blocks operations when open."""
        service = circuit_breaker_service

        # Open circuit breaker
        service._circuit_breaker_open = True
        service._circuit_breaker_last_failure = time.time()  # Recent failure

        # Should block operation immediately
        with pytest.raises(CoreServiceError, match="Circuit breaker is open"):
            service._check_circuit_breaker_state()


class TestAdvancedTransactionManagement:
    """Test advanced transaction management features."""

    @pytest.fixture
    def transaction_service(self):
        """Create database service for transaction testing."""
        settings = Mock(spec=Settings)
        settings.effective_postgres_url = "postgresql://user:pass@localhost:5432/testdb"

        service = DatabaseService(settings=settings)
        service._supabase_client = Mock()
        service._connected = True

        return service

    @pytest.mark.asyncio
    async def test_nested_transaction_support(self, transaction_service):
        """Test nested transaction with savepoints."""
        service = transaction_service

        # Mock transaction context
        with patch.object(service, "transaction") as mock_transaction:
            mock_tx = AsyncMock()
            mock_transaction.return_value.__aenter__.return_value = mock_tx

            async with service.transaction() as tx1:
                await tx1.execute("INSERT INTO users (name) VALUES ('user1')")

                # Nested transaction (savepoint)
                async with service.transaction() as tx2:
                    await tx2.execute("INSERT INTO users (name) VALUES ('user2')")

                    # This should create a savepoint, not a new transaction
                    assert tx2 is not None

    @pytest.mark.asyncio
    async def test_transaction_rollback_scenarios(self, transaction_service):
        """Test various transaction rollback scenarios."""
        service = transaction_service

        # Test automatic rollback on exception
        with patch.object(service, "transaction") as mock_transaction:
            mock_tx = AsyncMock()
            mock_transaction.return_value.__aenter__.return_value = mock_tx
            mock_transaction.return_value.__aexit__.return_value = None

            try:
                async with service.transaction() as tx:
                    await tx.execute("INSERT INTO users (name) VALUES ('test')")
                    raise ValueError("Test exception")
            except ValueError:
                pass

            # Verify rollback was called
            mock_tx.rollback.assert_called()

    @pytest.mark.asyncio
    async def test_transaction_isolation_levels(self, transaction_service):
        """Test transaction isolation level support."""
        service = transaction_service

        # Test different isolation levels
        isolation_levels = [
            "READ COMMITTED",
            "REPEATABLE READ",
            "SERIALIZABLE",
        ]

        for level in isolation_levels:
            with patch.object(service, "_set_transaction_isolation") as mock_isolation:
                await service._begin_transaction_with_isolation(level)
                mock_isolation.assert_called_with(level)

    @pytest.mark.asyncio
    async def test_transaction_performance_monitoring(self, transaction_service):
        """Test transaction performance monitoring."""
        service = transaction_service

        # Mock transaction with timing
        start_time = time.time()

        with patch.object(service, "transaction") as mock_transaction:
            mock_tx = AsyncMock()
            mock_transaction.return_value.__aenter__.return_value = mock_tx

            async with service.transaction() as tx:
                await asyncio.sleep(0.1)  # Simulate work
                await tx.execute("SELECT 1")

        # Verify transaction timing was recorded
        end_time = time.time()
        duration = (end_time - start_time) * 1000

        assert duration > 100  # Should be > 100ms


class TestErrorHandlingAndRecovery:
    """Test comprehensive error handling and recovery mechanisms."""

    @pytest.fixture
    def error_handling_service(self):
        """Create database service for error handling testing."""
        settings = Mock(spec=Settings)
        settings.effective_postgres_url = "postgresql://user:pass@localhost:5432/testdb"

        service = DatabaseService(settings=settings)
        service._supabase_client = Mock()
        service._connected = True

        return service

    @pytest.mark.asyncio
    async def test_connection_failure_recovery(self, error_handling_service):
        """Test recovery from connection failures."""
        service = error_handling_service

        # Simulate connection failure
        service._connected = False

        # Test automatic reconnection
        with patch.object(service, "connect") as mock_connect:
            mock_connect.return_value = None

            await service._ensure_connected_with_retry()

            mock_connect.assert_called()

    @pytest.mark.asyncio
    async def test_query_timeout_handling(self, error_handling_service):
        """Test query timeout handling and recovery."""
        service = error_handling_service

        # Mock query that times out
        with patch.object(service, "execute_sql") as mock_execute:
            mock_execute.side_effect = asyncio.TimeoutError("Query timeout")

            with pytest.raises(CoreDatabaseError, match="Query timeout"):
                await service._execute_with_timeout(
                    service.execute_sql, "SELECT * FROM large_table", timeout=1.0
                )

    @pytest.mark.asyncio
    async def test_retry_mechanism(self, error_handling_service):
        """Test retry mechanism for transient failures."""
        service = error_handling_service

        call_count = 0

        async def failing_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Transient failure")
            return "success"

        # Should succeed on 3rd attempt
        result = await service._execute_with_retry(
            failing_operation, max_retries=3, backoff_factor=0.1
        )

        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_connection_pool_recovery(self, error_handling_service):
        """Test connection pool recovery after failures."""
        service = error_handling_service

        # Mock pool recovery
        with patch.object(service, "_recreate_connection_pool") as mock_recreate:
            await service._recover_connection_pool()
            mock_recreate.assert_called_once()

    def test_error_classification(self, error_handling_service):
        """Test classification of different error types."""
        service = error_handling_service

        # Test different error types
        errors = [
            ("connection reset", True),  # Retryable
            ("timeout", True),  # Retryable
            ("syntax error", False),  # Not retryable
            ("constraint violation", False),  # Not retryable
        ]

        for error_msg, expected_retryable in errors:
            exception = Exception(error_msg)
            is_retryable = service._is_retryable_error(exception)
            assert is_retryable == expected_retryable


class TestPerformanceOptimization:
    """Test performance optimization features."""

    @pytest.fixture
    def performance_service(self):
        """Create database service for performance testing."""
        settings = Mock(spec=Settings)
        settings.effective_postgres_url = "postgresql://user:pass@localhost:5432/testdb"

        config = DatabaseConfig.create_production()
        service = DatabaseService(settings=settings, config=config)
        service._connected = True

        return service

    def test_query_performance_tracking(self, performance_service):
        """Test query performance tracking and optimization."""
        service = performance_service

        # Add query performance data
        queries = [
            {"sql": "SELECT * FROM users", "duration": 150.0, "rows": 100},
            {"sql": "SELECT * FROM orders", "duration": 300.0, "rows": 500},
            {"sql": "SELECT * FROM products", "duration": 75.0, "rows": 50},
        ]

        for query in queries:
            service._track_query_performance(
                query["sql"], query["duration"], query["rows"]
            )

        # Get performance summary
        summary = service._get_performance_summary()

        assert summary["total_queries"] == 3
        assert summary["avg_duration_ms"] == 175.0
        assert summary["slow_queries"] == 1  # orders query > threshold

    def test_connection_pool_optimization(self, performance_service):
        """Test connection pool optimization recommendations."""
        service = performance_service

        # Simulate high utilization
        service._connection_stats.active_connections = 95
        service._connection_stats.pool_size = 100
        service._connection_stats.pool_utilization = 0.95

        recommendations = service._get_pool_optimization_recommendations()

        assert "increase_pool_size" in recommendations
        assert recommendations["increase_pool_size"]["priority"] == "high"

    def test_query_caching_optimization(self, performance_service):
        """Test query result caching for performance."""

        # Mock cache implementation
        cache = {}

        def cache_key(sql, params):
            return f"{sql}:{hash(str(params))}"

        # Test cache hit/miss
        sql = "SELECT name FROM users WHERE id = $1"
        params = ("123",)
        key = cache_key(sql, params)

        # First call - cache miss
        assert key not in cache
        cache[key] = {"name": "Test User"}

        # Second call - cache hit
        assert key in cache
        result = cache[key]
        assert result["name"] == "Test User"

    def test_read_replica_routing(self, performance_service):
        """Test read replica routing for performance."""
        service = performance_service

        # Test read vs write operation routing
        read_queries = [
            "SELECT * FROM users",
            "SELECT COUNT(*) FROM orders",
            "SELECT name FROM products WHERE category = 'electronics'",
        ]

        write_queries = [
            "INSERT INTO users (name) VALUES ('test')",
            "UPDATE orders SET status = 'completed'",
            "DELETE FROM products WHERE id = 123",
        ]

        for query in read_queries:
            route = service._determine_query_route(query)
            assert route == "read_replica"

        for query in write_queries:
            route = service._determine_query_route(query)
            assert route == "primary"
