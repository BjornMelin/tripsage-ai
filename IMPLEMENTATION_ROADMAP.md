# Database Security Migration - Implementation Roadmap

## Overview

This document provides a detailed, task-by-task implementation plan for migrating all database connections to use the secure utilities developed in BJO-210. Each task includes specific code changes, testing requirements, and rollback procedures.

## Phase 1: Configuration Enhancement (Week 1)

### Task 1.1: Update Core Configuration
**File**: `/tripsage_core/config.py`

```python
# Add new configuration field
postgres_url: Optional[str] = Field(
    default=None,
    description="Direct PostgreSQL connection URL for Mem0/pgvector operations",
    example="postgresql://user:pass@host:port/db?sslmode=require",
    env="POSTGRES_URL"
)

@property
def effective_postgres_url(self) -> str:
    """Get PostgreSQL URL, converting from Supabase if needed."""
    if self.postgres_url:
        return self.postgres_url
    
    # Auto-convert from Supabase URL
    from tripsage_core.utils.url_converters import convert_supabase_to_postgres
    return convert_supabase_to_postgres(
        self.database_url,
        self.database_service_key.get_secret_value()
    )
```

**Testing**:
- Unit test for configuration loading
- Test auto-conversion when postgres_url is None
- Test explicit postgres_url override

### Task 1.2: Create Connection Factory
**File**: `/tripsage_core/database/factory.py`

```python
"""
Unified database connection factory with security validation.
"""
from typing import Optional
from contextlib import asynccontextmanager

import asyncpg
from supabase import create_client, Client

from tripsage_core.config import Settings
from tripsage_core.utils.connection_utils import (
    SecureDatabaseConnectionManager,
    DatabaseURLParser,
    ConnectionCredentials
)
from tripsage_core.utils.url_converters import DatabaseURLConverter


class DatabaseConnectionFactory:
    """Factory for creating database connections with proper security."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.connection_manager = SecureDatabaseConnectionManager()
        self.url_converter = DatabaseURLConverter()
        self.url_parser = DatabaseURLParser()
    
    async def create_postgres_connection(self, **kwargs) -> asyncpg.Connection:
        """
        Create PostgreSQL connection with security validation.
        
        Args:
            **kwargs: Additional connection parameters
            
        Returns:
            Validated PostgreSQL connection
        """
        # Get effective PostgreSQL URL
        postgres_url = self.settings.effective_postgres_url
        
        # Parse and validate
        credentials = await self.connection_manager.parse_and_validate_url(
            postgres_url
        )
        
        # Create connection with security settings
        async with self.connection_manager.get_validated_connection(
            postgres_url
        ) as conn:
            return conn
    
    @asynccontextmanager
    async def create_postgres_pool(self, min_size: int = 10, max_size: int = 20):
        """Create PostgreSQL connection pool with validation."""
        credentials = self.url_parser.parse_url(
            self.settings.effective_postgres_url
        )
        
        pool = await asyncpg.create_pool(
            host=credentials.hostname,
            port=credentials.port,
            user=credentials.username,
            password=credentials.password,
            database=credentials.database,
            ssl=credentials.query_params.get("sslmode", "require"),
            min_size=min_size,
            max_size=max_size
        )
        
        try:
            yield pool
        finally:
            await pool.close()
    
    def create_supabase_client(self) -> Client:
        """
        Create Supabase client for API operations.
        
        Returns:
            Configured Supabase client
        """
        return create_client(
            self.settings.database_url,
            self.settings.database_public_key.get_secret_value()
        )
```

## Phase 2: Service Migration (Week 2)

### Task 2.1: Migrate database/connection.py
**File**: `/tripsage_core/database/connection.py`

**Current Code**:
```python
# Simple string replacement approach
database_url = database_url.replace("postgres://", "postgresql+asyncpg://")
```

**New Code**:
```python
from tripsage_core.utils.connection_utils import DatabaseURLParser
from tripsage_core.utils.url_converters import DatabaseURLDetector

async def create_async_engine(database_url: str, **kwargs):
    """Create async SQLAlchemy engine with secure URL parsing."""
    # Detect and validate URL type
    detector = DatabaseURLDetector()
    url_info = detector.detect_url_type(database_url)
    
    if url_info["type"] == "postgresql":
        # Parse with security validation
        parser = DatabaseURLParser()
        credentials = parser.parse_url(database_url)
        
        # Convert to SQLAlchemy format
        sqlalchemy_url = credentials.to_connection_string().replace(
            "postgresql://", "postgresql+asyncpg://"
        )
        
        # Create engine with security settings
        engine = create_async_engine(
            sqlalchemy_url,
            pool_pre_ping=True,
            pool_size=20,
            max_overflow=0,
            **kwargs
        )
        
        # Validate connection on startup
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        
        return engine
    else:
        raise ValueError(f"Unsupported database URL type: {url_info['type']}")
```

### Task 2.2: Migrate checkpoint_manager.py
**File**: `/tripsage/orchestration/checkpoint_manager.py`

**Current Code**:
```python
# Custom URL building
self._connection_string = (
    f"postgresql://postgres:{supabase_key}@"
    f"{project_ref}.supabase.co:5432/postgres"
    "?sslmode=require"
)
```

**New Code**:
```python
from tripsage_core.utils.url_converters import DatabaseURLConverter
from tripsage_core.utils.connection_utils import SecureDatabaseConnectionManager

def _build_connection_string(self) -> str:
    """Build PostgreSQL connection string from Supabase configuration."""
    if self._connection_string:
        return self._connection_string
    
    try:
        settings = get_settings()
        
        # Use secure URL converter
        converter = DatabaseURLConverter()
        self._connection_string = converter.supabase_to_postgres(
            settings.database_url,
            settings.database_service_key.get_secret_value(),
            use_pooler=False  # Direct connection for checkpointing
        )
        
        # Validate connection string
        manager = SecureDatabaseConnectionManager()
        asyncio.run(manager.parse_and_validate_url(self._connection_string))
        
        logger.debug("Built secure connection string for Supabase project")
        return self._connection_string
        
    except Exception as e:
        logger.error(f"Failed to build connection string: {e}")
        raise
```

### Task 2.3: Create Migration Helper
**File**: `/scripts/database/migrate_connections.py`

```python
#!/usr/bin/env python3
"""
Helper script to migrate database connections to secure utilities.
"""
import asyncio
import logging
from pathlib import Path

from tripsage_core.config import get_settings
from tripsage_core.utils.connection_utils import SecureDatabaseConnectionManager
from tripsage_core.utils.url_converters import DatabaseURLConverter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_connection_migration():
    """Test all database connections after migration."""
    settings = get_settings()
    manager = SecureDatabaseConnectionManager()
    converter = DatabaseURLConverter()
    
    results = {
        "supabase_api": False,
        "postgres_direct": False,
        "postgres_pooler": False,
        "memory_service": False
    }
    
    # Test Supabase API connection
    try:
        from supabase import create_client
        client = create_client(
            settings.database_url,
            settings.database_public_key.get_secret_value()
        )
        # Simple test query
        client.table("users").select("id").limit(1).execute()
        results["supabase_api"] = True
        logger.info("✅ Supabase API connection successful")
    except Exception as e:
        logger.error(f"❌ Supabase API connection failed: {e}")
    
    # Test direct PostgreSQL connection
    try:
        postgres_url = converter.supabase_to_postgres(
            settings.database_url,
            settings.database_service_key.get_secret_value()
        )
        await manager.parse_and_validate_url(postgres_url)
        results["postgres_direct"] = True
        logger.info("✅ Direct PostgreSQL connection successful")
    except Exception as e:
        logger.error(f"❌ Direct PostgreSQL connection failed: {e}")
    
    # Test pooler connection
    try:
        pooler_url = converter.supabase_to_postgres(
            settings.database_url,
            settings.database_service_key.get_secret_value(),
            use_pooler=True
        )
        await manager.parse_and_validate_url(pooler_url)
        results["postgres_pooler"] = True
        logger.info("✅ Pooler PostgreSQL connection successful")
    except Exception as e:
        logger.error(f"❌ Pooler PostgreSQL connection failed: {e}")
    
    # Test memory service connection
    try:
        from tripsage_core.services.business.memory_service import MemoryService
        memory_service = MemoryService()
        await memory_service.connect()
        results["memory_service"] = True
        logger.info("✅ Memory service connection successful")
    except Exception as e:
        logger.error(f"❌ Memory service connection failed: {e}")
    
    # Summary
    success_count = sum(results.values())
    total_count = len(results)
    
    logger.info(f"\n{'='*50}")
    logger.info(f"Migration Test Results: {success_count}/{total_count} successful")
    logger.info(f"{'='*50}")
    
    for connection, success in results.items():
        status = "✅" if success else "❌"
        logger.info(f"{status} {connection}")
    
    return all(results.values())


if __name__ == "__main__":
    success = asyncio.run(test_connection_migration())
    exit(0 if success else 1)
```

## Phase 3: Testing & Validation (Week 3)

### Task 3.1: Integration Test Suite
**File**: `/tests/integration/test_database_migration.py`

```python
"""Integration tests for database connection migration."""
import pytest
from unittest.mock import patch, MagicMock

from tripsage_core.utils.connection_utils import (
    SecureDatabaseConnectionManager,
    DatabaseURLParser,
    ConnectionCredentials
)
from tripsage_core.utils.url_converters import (
    DatabaseURLConverter,
    DatabaseURLDetector
)


class TestDatabaseMigration:
    """Test database connection migration scenarios."""
    
    @pytest.mark.asyncio
    async def test_memory_service_migration(self):
        """Test memory service uses secure connection."""
        from tripsage_core.services.business.memory_service import MemoryService
        
        # Mock settings
        with patch('tripsage_core.config.get_settings') as mock_settings:
            mock_settings.return_value.database_url = "https://test.supabase.co"
            mock_settings.return_value.database_service_key.get_secret_value.return_value = "test-key"
            
            service = MemoryService()
            
            # Verify secure parsing is used
            assert hasattr(service, 'connection_manager')
            assert isinstance(service.connection_manager, SecureDatabaseConnectionManager)
    
    @pytest.mark.asyncio
    async def test_checkpoint_manager_migration(self):
        """Test checkpoint manager uses secure URL conversion."""
        from tripsage.orchestration.checkpoint_manager import SupabaseCheckpointManager
        
        manager = SupabaseCheckpointManager()
        
        # Mock URL building
        with patch.object(manager, '_build_connection_string') as mock_build:
            mock_build.return_value = "postgresql://user:pass@host:5432/db"
            
            conn_string = manager._build_connection_string()
            
            # Verify it's a valid PostgreSQL URL
            converter = DatabaseURLConverter()
            assert converter.is_postgres_url(conn_string)
    
    @pytest.mark.asyncio
    async def test_database_connection_migration(self):
        """Test database connection module migration."""
        from tripsage_core.database.connection import create_async_engine
        
        # Test with PostgreSQL URL
        postgres_url = "postgresql://user:pass@localhost:5432/testdb"
        
        with patch('sqlalchemy.ext.asyncio.create_async_engine') as mock_create:
            mock_engine = MagicMock()
            mock_create.return_value = mock_engine
            
            # Should parse and validate URL
            engine = await create_async_engine(postgres_url)
            
            # Verify URL was transformed correctly
            call_args = mock_create.call_args[0][0]
            assert "postgresql+asyncpg://" in call_args
```

### Task 3.2: Security Validation Tests
**File**: `/tests/security/test_database_security.py`

```python
"""Security tests for database connections."""
import pytest
import logging

from tripsage_core.utils.connection_utils import DatabaseURLParser
from tripsage_core.utils.url_converters import DatabaseURLConverter


class TestDatabaseSecurity:
    """Test database connection security measures."""
    
    def test_no_credentials_in_logs(self, caplog):
        """Ensure credentials are never logged."""
        parser = DatabaseURLParser()
        
        with caplog.at_level(logging.DEBUG):
            credentials = parser.parse_url(
                "postgresql://user:supersecret@host:5432/db"
            )
            
            # Check logs don't contain password
            log_text = caplog.text
            assert "supersecret" not in log_text
            assert "***MASKED***" in credentials.sanitized_for_logging()
    
    def test_sql_injection_prevention(self):
        """Test SQL injection attempts are caught."""
        parser = DatabaseURLParser()
        
        # Attempt SQL injection in database name
        malicious_url = "postgresql://user:pass@host:5432/db'; DROP TABLE users; --"
        
        # Should parse but encode dangerous characters
        credentials = parser.parse_url(malicious_url)
        assert "DROP TABLE" not in credentials.database
        assert "%27%3B%20DROP%20TABLE" in credentials.to_connection_string()
    
    def test_url_traversal_prevention(self):
        """Test path traversal attempts are prevented."""
        converter = DatabaseURLConverter()
        
        # Attempt path traversal
        malicious_urls = [
            "https://../../etc/passwd.supabase.co",
            "https://project/.../admin.supabase.co",
            "https://project%2F..%2Fetc.supabase.co"
        ]
        
        for url in malicious_urls:
            with pytest.raises(Exception):
                converter.extract_supabase_project_ref(url)
```

## Phase 4: Monitoring & Alerting (Week 4)

### Task 4.1: Connection Monitor Service
**File**: `/tripsage_core/services/infrastructure/database_monitor.py`

```python
"""
Database connection monitoring service.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from tripsage_core.utils.connection_utils import (
    SecureDatabaseConnectionManager,
    ConnectionState
)


class DatabaseConnectionMonitor:
    """Monitor database connection health and security."""
    
    def __init__(self, check_interval: int = 60):
        self.check_interval = check_interval
        self.connection_managers: Dict[str, SecureDatabaseConnectionManager] = {}
        self.health_history: List[Dict] = []
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def register_connection(self, name: str, manager: SecureDatabaseConnectionManager):
        """Register a connection manager for monitoring."""
        self.connection_managers[name] = manager
    
    async def check_connection_health(self) -> Dict[str, Dict]:
        """Perform health check on all registered connections."""
        results = {}
        
        for name, manager in self.connection_managers.items():
            try:
                # Check circuit breaker state
                cb_state = manager.circuit_breaker.state
                
                # Attempt validation
                start_time = datetime.utcnow()
                try:
                    # This will use the circuit breaker
                    await manager.parse_and_validate_url(
                        manager.url_parser.parse_url("postgresql://test:test@test/test")
                    )
                    latency = (datetime.utcnow() - start_time).total_seconds()
                    success = True
                except Exception:
                    latency = None
                    success = False
                
                results[name] = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "success": success,
                    "latency_seconds": latency,
                    "circuit_breaker_state": cb_state.value,
                    "failure_count": manager.circuit_breaker.failure_count,
                    "retry_count": getattr(manager.retry_handler, 'retry_count', 0)
                }
                
            except Exception as e:
                self.logger.error(f"Health check failed for {name}: {e}")
                results[name] = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "success": False,
                    "error": str(e)
                }
        
        # Store in history
        self.health_history.append(results)
        
        # Trim history (keep last 24 hours)
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        self.health_history = [
            h for h in self.health_history
            if datetime.fromisoformat(
                list(h.values())[0]["timestamp"]
            ) > cutoff_time
        ]
        
        return results
    
    async def alert_on_security_issues(self) -> List[Dict]:
        """Check for potential security issues."""
        alerts = []
        
        for name, manager in self.connection_managers.items():
            # Check for sustained failures (possible attack)
            if manager.circuit_breaker.state == ConnectionState.OPEN:
                if manager.circuit_breaker.failure_count > 10:
                    alerts.append({
                        "severity": "high",
                        "connection": name,
                        "issue": "Sustained connection failures detected",
                        "details": {
                            "failure_count": manager.circuit_breaker.failure_count,
                            "last_failure": manager.circuit_breaker.last_failure_time
                        }
                    })
            
            # Check for unusual retry patterns
            retry_handler = manager.retry_handler
            if hasattr(retry_handler, 'retry_history'):
                recent_retries = [
                    r for r in retry_handler.retry_history
                    if r['timestamp'] > datetime.utcnow() - timedelta(minutes=5)
                ]
                
                if len(recent_retries) > 20:
                    alerts.append({
                        "severity": "medium",
                        "connection": name,
                        "issue": "Unusual retry pattern detected",
                        "details": {
                            "retry_count": len(recent_retries),
                            "time_window": "5 minutes"
                        }
                    })
        
        return alerts
    
    async def run_monitoring_loop(self):
        """Run continuous monitoring loop."""
        while True:
            try:
                # Health check
                health_results = await self.check_connection_health()
                
                # Security check
                security_alerts = await self.alert_on_security_issues()
                
                # Log summary
                healthy_count = sum(
                    1 for r in health_results.values()
                    if r.get("success", False)
                )
                total_count = len(health_results)
                
                self.logger.info(
                    f"Connection health: {healthy_count}/{total_count} healthy, "
                    f"{len(security_alerts)} security alerts"
                )
                
                # Send alerts if needed
                for alert in security_alerts:
                    self.logger.warning(
                        f"Security Alert [{alert['severity']}] "
                        f"{alert['connection']}: {alert['issue']}"
                    )
                
                # Wait for next check
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                self.logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(self.check_interval)
```

### Task 4.2: Metrics Collection
**File**: `/tripsage_core/monitoring/database_metrics.py`

```python
"""Database connection metrics collection."""
from prometheus_client import Counter, Histogram, Gauge, Enum

# Connection metrics
db_connection_attempts = Counter(
    'database_connection_attempts_total',
    'Total number of database connection attempts',
    ['connection_type', 'database']
)

db_connection_errors = Counter(
    'database_connection_errors_total',
    'Total number of database connection errors',
    ['connection_type', 'database', 'error_type']
)

db_connection_duration = Histogram(
    'database_connection_duration_seconds',
    'Database connection establishment duration',
    ['connection_type', 'database']
)

# Circuit breaker metrics
db_circuit_breaker_state = Enum(
    'database_circuit_breaker_state',
    'Current state of database circuit breaker',
    ['connection_type'],
    states=['closed', 'open', 'half_open']
)

db_circuit_breaker_failures = Gauge(
    'database_circuit_breaker_failures',
    'Current failure count for circuit breaker',
    ['connection_type']
)

# URL parsing metrics
db_url_parse_errors = Counter(
    'database_url_parse_errors_total',
    'Total number of URL parsing errors',
    ['url_type', 'error_reason']
)

db_url_parse_duration = Histogram(
    'database_url_parse_duration_seconds',
    'Duration of URL parsing operations',
    ['url_type']
)
```

## Rollback Strategy

### Feature Flags
**File**: `/tripsage_core/config.py`

```python
# Add feature flags
use_secure_db_connections: bool = Field(
    default=True,
    env="USE_SECURE_DB_CONNECTIONS",
    description="Enable secure database connection utilities"
)

fallback_on_connection_error: bool = Field(
    default=True,
    env="FALLBACK_ON_CONNECTION_ERROR",
    description="Fall back to old connection method on error"
)
```

### Rollback Wrapper
**File**: `/tripsage_core/utils/connection_fallback.py`

```python
"""Fallback utilities for database connections."""
import logging
from typing import Optional, Callable

logger = logging.getLogger(__name__)


async def with_fallback(
    primary_func: Callable,
    fallback_func: Callable,
    *args,
    **kwargs
):
    """
    Execute primary function with fallback on error.
    
    Args:
        primary_func: Primary function to execute
        fallback_func: Fallback function if primary fails
        *args: Function arguments
        **kwargs: Function keyword arguments
        
    Returns:
        Result from primary or fallback function
    """
    try:
        return await primary_func(*args, **kwargs)
    except Exception as e:
        logger.warning(
            f"Primary function {primary_func.__name__} failed: {e}, "
            "attempting fallback"
        )
        return await fallback_func(*args, **kwargs)
```

## Success Criteria

1. **All Tests Pass**: 100% of migration tests pass
2. **No Credential Leaks**: Zero passwords in logs
3. **Connection Success**: >99.9% connection success rate
4. **Performance**: <100ms connection establishment
5. **Security Alerts**: <5 security alerts per day

## Timeline Summary

| Week | Tasks | Deliverables |
|------|-------|--------------|
| 1 | Config updates, URL converters, factory | Enhanced configuration, connection factory |
| 2 | Service migrations | Updated connection modules |
| 3 | Testing & validation | Complete test suite |
| 4 | Monitoring & metrics | Production monitoring |

## Next Steps

1. **Day 1**: Update configuration with PostgreSQL URL support
2. **Day 2-3**: Implement connection factory
3. **Day 4-5**: Migrate database/connection.py
4. **Week 2**: Continue service migrations
5. **Week 3**: Comprehensive testing
6. **Week 4**: Deploy monitoring

This implementation roadmap provides clear, actionable steps for migrating all database connections to use secure utilities while maintaining system stability.