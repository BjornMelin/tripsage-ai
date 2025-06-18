"""
Comprehensive integration tests for API key validation full stack flow.

This module provides end-to-end integration testing covering:
- FastAPI HTTP endpoints with TestClient
- Service layer business logic
- Database transactions and persistence
- Cache integration and fallback behavior
- Error propagation through the entire stack
- Concurrent operations and thread safety
- External API validation with retry mechanisms

Following modern testing patterns (2025) with real dependencies where possible.
"""

import asyncio
import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import redis.asyncio as redis
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from tripsage.api.main import app
from tripsage_core.services.business.api_key_service import (
    ApiKeyCreateRequest,
    ApiKeyService,
    ServiceType,
    ValidationStatus,
)

logger = logging.getLogger(__name__)

class TestDatabaseService:
    """Lightweight test database service for integration tests."""

    def __init__(self, engine):
        self.engine = engine
        self._transaction_stack = []

    async def insert(self, table: str, data: dict[str, Any]) -> list[dict[str, Any]]:
        """Insert data into table."""
        async with self.engine.begin() as conn:
            # Build INSERT statement
            columns = ", ".join(data.keys())
            placeholders = ", ".join(f":{key}" for key in data.keys())

            result = await conn.execute(
                text(
                    f"INSERT INTO {table} ({columns}) VALUES ({placeholders}) "
                    f"RETURNING *"
                ),
                data,
            )
            return [dict(row._mapping) for row in result.fetchall()]

    async def select(
        self, table: str, filters: dict[str, Any] | None = None, columns: str = "*"
    ) -> list[dict[str, Any]]:
        """Select data from table."""
        async with self.engine.begin() as conn:
            query = f"SELECT {columns} FROM {table}"
            params = {}

            if filters:
                conditions = []
                for key, value in filters.items():
                    conditions.append(f"{key} = :{key}")
                    params[key] = value
                query += f" WHERE {' AND '.join(conditions)}"

            result = await conn.execute(text(query), params)
            return [dict(row._mapping) for row in result.fetchall()]

    async def update(
        self, table: str, data: dict[str, Any], filters: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Update data in table."""
        async with self.engine.begin() as conn:
            set_clauses = []
            params = {}

            for key, value in data.items():
                set_clauses.append(f"{key} = :set_{key}")
                params[f"set_{key}"] = value

            conditions = []
            for key, value in filters.items():
                conditions.append(f"{key} = :where_{key}")
                params[f"where_{key}"] = value

            query = (
                f"UPDATE {table} SET {', '.join(set_clauses)} "
                f"WHERE {' AND '.join(conditions)} RETURNING *"
            )
            result = await conn.execute(text(query), params)
            return [dict(row._mapping) for row in result.fetchall()]

    async def delete(self, table: str, filters: dict[str, Any]) -> int:
        """Delete data from table."""
        async with self.engine.begin() as conn:
            conditions = []
            params = {}

            for key, value in filters.items():
                conditions.append(f"{key} = :{key}")
                params[key] = value

            query = f"DELETE FROM {table} WHERE {' AND '.join(conditions)}"
            result = await conn.execute(text(query), params)
            return result.rowcount

    @asynccontextmanager
    async def transaction(self):
        """Transaction context manager."""
        transaction_ops = []

        class TransactionContext:
            def __init__(self, ops):
                self.ops = ops

            def insert(self, table: str, data: dict[str, Any]):
                self.ops.append(("insert", table, data))

            def update(self, table: str, data: dict[str, Any], filters: dict[str, Any]):
                self.ops.append(("update", table, data, filters))

            def delete(self, table: str, filters: dict[str, Any]):
                self.ops.append(("delete", table, filters))

            async def execute(self):
                results = []
                async with self.parent.engine.begin() as conn:
                    for op in self.ops:
                        if op[0] == "insert":
                            _, table, data = op
                            columns = ", ".join(data.keys())
                            placeholders = ", ".join(f":{key}" for key in data.keys())
                            result = await conn.execute(
                                text(
                                    f"INSERT INTO {table} ({columns}) VALUES "
                                    f"({placeholders}) RETURNING *"
                                ),
                                data,
                            )
                            results.append(
                                [dict(row._mapping) for row in result.fetchall()]
                            )
                        elif op[0] == "update":
                            _, table, data, filters = op
                            set_clauses = []
                            params = {}

                            for key, value in data.items():
                                set_clauses.append(f"{key} = :set_{key}")
                                params[f"set_{key}"] = value

                            conditions = []
                            for key, value in filters.items():
                                conditions.append(f"{key} = :where_{key}")
                                params[f"where_{key}"] = value

                            query = (
                                f"UPDATE {table} SET {', '.join(set_clauses)} "
                                f"WHERE {' AND '.join(conditions)} RETURNING *"
                            )
                            result = await conn.execute(text(query), params)
                            results.append(
                                [dict(row._mapping) for row in result.fetchall()]
                            )
                        elif op[0] == "delete":
                            _, table, filters = op
                            conditions = []
                            params = {}

                            for key, value in filters.items():
                                conditions.append(f"{key} = :{key}")
                                params[key] = value

                            query = (
                                f"DELETE FROM {table} WHERE {' AND '.join(conditions)}"
                            )
                            result = await conn.execute(text(query), params)
                            results.append(result.rowcount)

                return results

        ctx = TransactionContext(transaction_ops)
        ctx.parent = self
        yield ctx

    # Methods required by ApiKeyService
    async def get_user_api_keys(self, user_id: str) -> list[dict[str, Any]]:
        """Get all API keys for a user."""
        return await self.select("api_keys", {"user_id": user_id})

    async def get_api_key_for_service(
        self, user_id: str, service: str
    ) -> dict[str, Any] | None:
        """Get API key for specific service."""
        results = await self.select(
            "api_keys", {"user_id": user_id, "service": service}
        )
        return results[0] if results else None

    async def get_api_key_by_id(
        self, key_id: str, user_id: str
    ) -> dict[str, Any] | None:
        """Get API key by ID and user."""
        results = await self.select("api_keys", {"id": key_id, "user_id": user_id})
        return results[0] if results else None

    async def update_api_key_last_used(self, key_id: str):
        """Update last used timestamp."""
        await self.update(
            "api_keys",
            {"last_used": datetime.now(timezone.utc).isoformat()},
            {"id": key_id},
        )

class TestCacheService:
    """Lightweight test cache service."""

    def __init__(self, redis_client):
        self.redis = redis_client

    async def get(self, key: str) -> str | None:
        """Get value from cache."""
        return await self.redis.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> bool:
        """Set value in cache."""
        return await self.redis.set(key, value, ex=ex)

    async def delete(self, key: str) -> int:
        """Delete key from cache."""
        return await self.redis.delete(key)

# Test Fixtures

@pytest.fixture(scope="session")
async def test_db_engine():
    """Create test database engine with proper schema."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True,
    )

    # Create tables with full schema
    async with engine.begin() as conn:
        await conn.execute(
            text("""
            CREATE TABLE api_keys (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                service TEXT NOT NULL,
                encrypted_key TEXT NOT NULL,
                description TEXT,
                is_valid BOOLEAN DEFAULT TRUE,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now')),
                expires_at TEXT,
                last_used TEXT,
                last_validated TEXT,
                usage_count INTEGER DEFAULT 0
            )
        """)
        )

        await conn.execute(
            text("""
            CREATE TABLE api_key_usage_logs (
                id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
                key_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                service TEXT NOT NULL,
                operation TEXT NOT NULL,
                success BOOLEAN NOT NULL,
                timestamp TEXT DEFAULT (datetime('now')),
                response_time REAL,
                error_message TEXT,
                FOREIGN KEY (key_id) REFERENCES api_keys (id)
            )
        """)
        )

        # Create users table for FK constraints
        await conn.execute(
            text("""
            CREATE TABLE users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                username TEXT UNIQUE,
                full_name TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now')),
                is_active BOOLEAN DEFAULT TRUE,
                is_verified BOOLEAN DEFAULT FALSE
            )
        """)
        )

    yield engine
    await engine.dispose()

@pytest.fixture(scope="session")
async def test_redis():
    """Create test Redis connection."""
    try:
        redis_client = redis.from_url(
            os.getenv("TEST_REDIS_URL", "redis://localhost:6379/15"),
            decode_responses=True,
        )
        await redis_client.ping()
        yield redis_client
        await redis_client.flushdb()
        await redis_client.close()
    except Exception:
        # Fallback to mock Redis for CI environments
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None
        mock_redis.set.return_value = True
        mock_redis.delete.return_value = 1
        mock_redis.ping.return_value = True
        mock_redis.flushdb.return_value = True
        mock_redis.close.return_value = None
        yield mock_redis

@pytest.fixture
async def test_db_service(test_db_engine):
    """Create test database service."""
    return TestDatabaseService(test_db_engine)

@pytest.fixture
async def test_cache_service(test_redis):
    """Create test cache service."""
    return TestCacheService(test_redis)

@pytest.fixture
async def api_key_service(test_db_service, test_cache_service):
    """Create ApiKeyService with test dependencies."""
    from tripsage_core.config import get_settings

    settings = get_settings()
    service = ApiKeyService(
        db=test_db_service,
        cache=test_cache_service,
        settings=settings,
        validation_timeout=5,  # Shorter timeout for tests
    )

    return service

@pytest.fixture
async def test_user(test_db_service):
    """Create a test user."""
    user_id = str(uuid.uuid4())
    user_data = {
        "id": user_id,
        "email": "test@example.com",
        "username": "testuser",
        "full_name": "Test User",
        "is_active": True,
        "is_verified": True,
    }

    await test_db_service.insert("users", user_data)
    return user_data

@pytest.fixture
def test_client():
    """Create FastAPI test client."""
    return TestClient(app)

# Integration Test Classes

class TestApiKeyFullStackIntegration:
    """Full stack integration tests for API key management."""

    @pytest.mark.asyncio
    async def test_complete_api_key_lifecycle_via_http(self, test_client, test_user):
        """Test complete API key lifecycle through HTTP endpoints."""
        user_id = test_user["id"]

        # Mock authentication to return our test user
        with patch(
            "tripsage.api.core.dependencies.get_principal_id", return_value=user_id
        ):
            with patch("tripsage.api.core.dependencies.require_principal") as mock_auth:
                mock_principal = MagicMock()
                mock_principal.user_id = user_id
                mock_auth.return_value = mock_principal

                # Mock external API validation
                with patch("httpx.AsyncClient.get") as mock_get:
                    mock_response = MagicMock()
                    mock_response.status_code = 200
                    mock_response.json.return_value = {"data": [{"id": "gpt-4"}]}
                    mock_get.return_value = mock_response

                    # 1. Create API key
                    create_data = {
                        "name": "Test Integration Key",
                        "service": "openai",
                        "key": "sk-test_integration_key_12345",
                        "description": "Integration test key",
                    }

                    response = test_client.post("/api/keys", json=create_data)
                    assert response.status_code == 201

                    created_key = response.json()
                    assert created_key["name"] == create_data["name"]
                    assert created_key["service"] == create_data["service"]
                    assert created_key["is_valid"] is True
                    key_id = created_key["id"]

                    # 2. List API keys
                    response = test_client.get("/api/keys")
                    assert response.status_code == 200

                    keys = response.json()
                    assert len(keys) == 1
                    assert keys[0]["id"] == key_id

                    # 3. Validate API key
                    validate_data = {
                        "service": "openai",
                        "key": "sk-test_validation_key",
                    }

                    response = test_client.post(
                        "/api/keys/validate", json=validate_data
                    )
                    assert response.status_code == 200

                    validation_result = response.json()
                    assert validation_result["is_valid"] is True
                    assert validation_result["service"] == "openai"

                    # 4. Rotate API key
                    rotate_data = {"new_key": "sk-rotated_integration_key_67890"}

                    response = test_client.post(
                        f"/api/keys/{key_id}/rotate", json=rotate_data
                    )
                    assert response.status_code == 200

                    rotated_key = response.json()
                    assert rotated_key["id"] == key_id
                    assert rotated_key["is_valid"] is True

                    # 5. Delete API key
                    response = test_client.delete(f"/api/keys/{key_id}")
                    assert response.status_code == 204

                    # 6. Verify deletion
                    response = test_client.get("/api/keys")
                    assert response.status_code == 200

                    keys = response.json()
                    assert len(keys) == 0

    @pytest.mark.asyncio
    async def test_database_transaction_rollback(self, api_key_service, test_user):
        """Test database transaction rollback scenarios."""
        user_id = test_user["id"]

        # Mock validation to succeed initially
        with patch.object(api_key_service, "validate_api_key") as mock_validate:
            mock_validate.return_value = MagicMock(
                is_valid=True,
                status=ValidationStatus.VALID,
                service=ServiceType.OPENAI,
                message="Valid",
                validated_at=datetime.now(timezone.utc),
            )

            # Create request
            request = ApiKeyCreateRequest(
                name="Transaction Test Key",
                service=ServiceType.OPENAI,
                key_value="sk-transaction_test_key",
                description="Test transaction rollback",
            )

            # Mock database transaction to fail after first operation
            original_execute = api_key_service.db.transaction

            @asynccontextmanager
            async def failing_transaction():
                tx = MagicMock()
                tx.insert = MagicMock()
                tx.execute = AsyncMock(side_effect=Exception("Database error"))
                yield tx

            api_key_service.db.transaction = failing_transaction

            # Attempt to create key - should fail and rollback
            with pytest.raises((Exception, RuntimeError)):  # Database/mock error
                await api_key_service.create_api_key(user_id, request)

            # Restore original transaction method
            api_key_service.db.transaction = original_execute

            # Verify no keys were created (transaction rolled back)
            keys = await api_key_service.list_user_keys(user_id)
            assert len(keys) == 0

    @pytest.mark.asyncio
    async def test_cache_integration_and_fallback(self, api_key_service, test_user):
        """Test cache integration and fallback behavior."""
        user_id = test_user["id"]
        test_key = "sk-cache_integration_test"

        # Mock external API
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": [{"id": "gpt-4"}]}
            mock_get.return_value = mock_response

            # First validation - should hit external API and cache result
            result1 = await api_key_service.validate_api_key(
                ServiceType.OPENAI, test_key, user_id
            )
            assert result1.is_valid is True
            assert mock_get.call_count == 1

            # Second validation - should use cache
            result2 = await api_key_service.validate_api_key(
                ServiceType.OPENAI, test_key, user_id
            )
            assert result2.is_valid is True
            assert mock_get.call_count == 1  # No additional API call

            # Test cache failure fallback
            original_get = api_key_service.cache.get
            api_key_service.cache.get = AsyncMock(side_effect=Exception("Cache error"))

            # Should fallback to external API
            result3 = await api_key_service.validate_api_key(
                ServiceType.OPENAI, "sk-fallback_test", user_id
            )
            assert result3.is_valid is True
            assert mock_get.call_count == 2  # Additional API call due to cache failure

            # Restore cache
            api_key_service.cache.get = original_get

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, api_key_service, test_user):
        """Test concurrent database operations and thread safety."""
        user_id = test_user["id"]

        async def create_test_key(index: int):
            """Create a test key with unique values."""
            request = ApiKeyCreateRequest(
                name=f"Concurrent Key {index}",
                service=ServiceType.OPENAI,
                key_value=f"sk-concurrent_test_{index}_{uuid.uuid4().hex[:8]}",
                description=f"Concurrent test key {index}",
            )

            # Mock validation for each key
            with patch.object(api_key_service, "validate_api_key") as mock_validate:
                mock_validate.return_value = MagicMock(
                    is_valid=True,
                    status=ValidationStatus.VALID,
                    service=ServiceType.OPENAI,
                    message="Valid",
                    validated_at=datetime.now(timezone.utc),
                )

                return await api_key_service.create_api_key(user_id, request)

        # Create 10 keys concurrently
        tasks = [create_test_key(i) for i in range(10)]
        created_keys = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify all operations succeeded
        successful_keys = [k for k in created_keys if not isinstance(k, Exception)]
        assert len(successful_keys) == 10

        # Verify all keys are in database
        user_keys = await api_key_service.list_user_keys(user_id)
        assert len(user_keys) == 10

        # Test concurrent deletion
        delete_tasks = [
            api_key_service.delete_api_key(key.id, user_id) for key in successful_keys
        ]
        delete_results = await asyncio.gather(*delete_tasks)

        # Verify all deletions succeeded
        assert all(delete_results)

        # Verify all keys are gone
        remaining_keys = await api_key_service.list_user_keys(user_id)
        assert len(remaining_keys) == 0

    @pytest.mark.asyncio
    async def test_error_propagation_full_stack(self, test_client, test_user):
        """Test error propagation from service layer to API responses."""
        user_id = test_user["id"]

        with patch(
            "tripsage.api.core.dependencies.get_principal_id", return_value=user_id
        ):
            with patch("tripsage.api.core.dependencies.require_principal") as mock_auth:
                mock_principal = MagicMock()
                mock_principal.user_id = user_id
                mock_auth.return_value = mock_principal

                # Test validation failure propagation
                with patch("httpx.AsyncClient.get") as mock_get:
                    mock_response = MagicMock()
                    mock_response.status_code = 401
                    mock_get.return_value = mock_response

                    create_data = {
                        "name": "Invalid Key Test",
                        "service": "openai",
                        "key": "sk-invalid_key",
                        "description": "Test invalid key",
                    }

                    response = test_client.post("/api/keys", json=create_data)
                    assert response.status_code == 400
                    assert "Invalid API key" in response.json()["detail"]

                # Test service error propagation
                with patch("httpx.AsyncClient.get") as mock_get:
                    mock_get.side_effect = Exception("Service unavailable")

                    validate_data = {
                        "service": "openai",
                        "key": "sk-service_error_test",
                    }

                    response = test_client.post(
                        "/api/keys/validate", json=validate_data
                    )
                    assert response.status_code == 200  # Service handles gracefully

                    result = response.json()
                    assert result["is_valid"] is False
                    assert result["status"] == "service_error"

    @pytest.mark.asyncio
    async def test_external_api_retry_mechanisms(self, api_key_service, test_user):
        """Test external API integration with retry mechanisms."""
        user_id = test_user["id"]

        # Test retry on timeout
        with patch("httpx.AsyncClient.get") as mock_get:
            # First two calls timeout, third succeeds
            mock_get.side_effect = [
                httpx.TimeoutException("Timeout 1"),
                httpx.ConnectError("Connection error"),
                MagicMock(status_code=200, json=lambda: {"data": [{"id": "gpt-4"}]}),
            ]

            result = await api_key_service.validate_api_key(
                ServiceType.OPENAI, "sk-retry_test", user_id
            )

            # Should succeed after retries
            assert result.is_valid is True
            assert mock_get.call_count == 3

    @pytest.mark.asyncio
    async def test_service_health_monitoring(self, api_key_service):
        """Test service health monitoring across multiple services."""
        # Mock health check responses
        with patch("httpx.AsyncClient.get") as mock_get:

            def mock_health_response(url, **kwargs):
                response = MagicMock()
                if "openai.com" in url:
                    response.status_code = 200
                    response.json.return_value = {
                        "status": {
                            "indicator": "none",
                            "description": "All systems operational",
                        }
                    }
                elif "openweathermap.org" in url:
                    response.status_code = 401  # Expected for invalid key
                elif "googleapis.com" in url:
                    response.status_code = 200
                    response.json.return_value = {"status": "REQUEST_DENIED"}
                return response

            mock_get.side_effect = mock_health_response

            # Test individual service health
            openai_health = await api_key_service.check_service_health(
                ServiceType.OPENAI
            )
            assert openai_health.is_healthy is True

            weather_health = await api_key_service.check_service_health(
                ServiceType.WEATHER
            )
            assert weather_health.is_healthy is True  # 401 is expected for health check

            # Test all services health check
            all_health = await api_key_service.check_all_services_health()
            assert len(all_health) == 3
            assert all(health.status != "unhealthy" for health in all_health.values())

    @pytest.mark.asyncio
    async def test_encryption_across_full_stack(self, api_key_service, test_user):
        """Test encryption/decryption across the full stack."""
        user_id = test_user["id"]

        with patch.object(api_key_service, "validate_api_key") as mock_validate:
            mock_validate.return_value = MagicMock(
                is_valid=True,
                status=ValidationStatus.VALID,
                service=ServiceType.OPENAI,
                message="Valid",
                validated_at=datetime.now(timezone.utc),
            )

            # Create key with sensitive data
            original_key = "sk-very_secret_and_sensitive_key_12345"
            request = ApiKeyCreateRequest(
                name="Encryption Test Key",
                service=ServiceType.OPENAI,
                key_value=original_key,
                description="Test encryption",
            )

            # Create and verify encryption
            created_key = await api_key_service.create_api_key(user_id, request)

            # Retrieve the encrypted key from database
            db_key = await api_key_service.db.get_api_key_by_id(created_key.id, user_id)
            assert db_key["encrypted_key"] != original_key  # Should be encrypted

            # Test decryption through service method
            decrypted_key = await api_key_service.get_key_for_service(
                user_id, ServiceType.OPENAI
            )
            assert decrypted_key == original_key  # Should match original

    @pytest.mark.asyncio
    async def test_audit_logging_integration(self, api_key_service, test_user):
        """Test audit logging integration across operations."""
        user_id = test_user["id"]

        with patch.object(api_key_service, "validate_api_key") as mock_validate:
            mock_validate.return_value = MagicMock(
                is_valid=True,
                status=ValidationStatus.VALID,
                service=ServiceType.OPENAI,
                message="Valid",
                validated_at=datetime.now(timezone.utc),
            )

            # Mock audit logging
            with patch(
                "tripsage_core.services.business.audit_logging_service.audit_api_key"
            ) as mock_audit:
                mock_audit.return_value = None

                # Create key
                request = ApiKeyCreateRequest(
                    name="Audit Test Key",
                    service=ServiceType.OPENAI,
                    key_value="sk-audit_test_key",
                    description="Test audit logging",
                )

                created_key = await api_key_service.create_api_key(user_id, request)

                # Give audit logging time to complete (it's fire-and-forget)
                await asyncio.sleep(0.1)

                # Verify audit logging was called for creation
                assert mock_audit.call_count >= 1

                # Delete key
                await api_key_service.delete_api_key(created_key.id, user_id)

                # Give audit logging time to complete
                await asyncio.sleep(0.1)

                # Verify audit logging was called for deletion
                assert mock_audit.call_count >= 2

class TestApiKeyValidationEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_malformed_requests(self, test_client, test_user):
        """Test handling of malformed requests."""
        user_id = test_user["id"]

        with patch(
            "tripsage.api.core.dependencies.get_principal_id", return_value=user_id
        ):
            with patch("tripsage.api.core.dependencies.require_principal") as mock_auth:
                mock_principal = MagicMock()
                mock_principal.user_id = user_id
                mock_auth.return_value = mock_principal

                # Missing required fields
                response = test_client.post("/api/keys", json={})
                assert response.status_code == 422

                # Invalid service type
                response = test_client.post(
                    "/api/keys",
                    json={
                        "name": "Test",
                        "service": "invalid_service",
                        "key": "test-key",
                    },
                )
                assert response.status_code == 422

                # Key too short
                response = test_client.post(
                    "/api/keys",
                    json={"name": "Test", "service": "openai", "key": "short"},
                )
                assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_rate_limiting_behavior(self, api_key_service, test_user, test_redis):
        """Test rate limiting behavior."""
        user_id = test_user["id"]

        # Simulate rate limiting
        for _i in range(15):  # Exceed typical limit
            await test_redis.incr(f"rate_limit:{user_id}")
            await test_redis.expire(f"rate_limit:{user_id}", 60)

        # Mock the rate limiting check if it exists
        if hasattr(api_key_service, "_is_rate_limited"):
            is_limited = await api_key_service._is_rate_limited(user_id)
            assert is_limited is True

        # Clean up
        await test_redis.delete(f"rate_limit:{user_id}")

    @pytest.mark.asyncio
    async def test_database_constraint_violations(self, test_db_service, test_user):
        """Test database constraint violations."""
        user_id = test_user["id"]

        # Create initial key
        key_data = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": "Test Key",
            "service": "openai",
            "encrypted_key": "encrypted_data",
            "is_valid": True,
        }

        await test_db_service.insert("api_keys", key_data)

        # Try to create duplicate with same ID
        with pytest.raises((Exception, ValueError)):  # Primary key constraint violation
            await test_db_service.insert("api_keys", key_data)

    @pytest.mark.asyncio
    async def test_cache_corruption_recovery(
        self, api_key_service, test_user, test_cache_service
    ):
        """Test recovery from cache corruption."""
        user_id = test_user["id"]

        # Set corrupted data in cache
        await test_cache_service.set(
            "api_validation:v2:test_hash", "corrupted_json_data"
        )

        # Validation should still work (fallback to external API)
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": [{"id": "gpt-4"}]}
            mock_get.return_value = mock_response

            result = await api_key_service.validate_api_key(
                ServiceType.OPENAI, "sk-corruption_test", user_id
            )

            assert result.is_valid is True
            assert mock_get.call_count == 1  # Should have hit external API

# Performance and Load Testing

class TestApiKeyPerformance:
    """Performance and load testing for API key operations."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_bulk_operations_performance(self, api_key_service, test_user):
        """Test performance of bulk operations."""
        user_id = test_user["id"]

        # Mock validation for performance testing
        with patch.object(api_key_service, "validate_api_key") as mock_validate:
            mock_validate.return_value = MagicMock(
                is_valid=True,
                status=ValidationStatus.VALID,
                service=ServiceType.OPENAI,
                message="Valid",
                validated_at=datetime.now(timezone.utc),
            )

            start_time = datetime.now()

            # Create 50 keys
            tasks = []
            for i in range(50):
                request = ApiKeyCreateRequest(
                    name=f"Bulk Key {i}",
                    service=ServiceType.OPENAI,
                    key_value=f"sk-bulk_test_{i}_{uuid.uuid4().hex[:8]}",
                    description=f"Bulk test key {i}",
                )
                tasks.append(api_key_service.create_api_key(user_id, request))

            created_keys = await asyncio.gather(*tasks)

            creation_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"Created 50 keys in {creation_time:.2f} seconds")

            # Performance assertion (should complete within reasonable time)
            assert creation_time < 10.0  # 10 seconds max for 50 keys
            assert len(created_keys) == 50

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_concurrent_validation_load(self, api_key_service, test_user):
        """Test concurrent validation load."""
        user_id = test_user["id"]

        # Mock external API with some latency
        async def mock_api_call(*args, **kwargs):
            await asyncio.sleep(0.1)  # Simulate API latency
            response = MagicMock()
            response.status_code = 200
            response.json.return_value = {"data": [{"id": "gpt-4"}]}
            return response

        with patch("httpx.AsyncClient.get", side_effect=mock_api_call):
            start_time = datetime.now()

            # 20 concurrent validations
            tasks = [
                api_key_service.validate_api_key(
                    ServiceType.OPENAI, f"sk-load_test_{i}", user_id
                )
                for i in range(20)
            ]

            results = await asyncio.gather(*tasks)

            total_time = (datetime.now() - start_time).total_seconds()
            logger.info(
                f"Completed 20 concurrent validations in {total_time:.2f} seconds"
            )

            # Should complete concurrently (not sequentially)
            assert total_time < 1.0  # Much faster than 20 * 0.1 = 2 seconds
            assert all(result.is_valid for result in results)
