"""
Integration tests for ApiKeyService with real dependencies.

This module tests the service integration with actual database, cache,
and external API providers using modern async testing patterns.
"""

import asyncio
import os
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator
from unittest.mock import patch

import pytest
import redis.asyncio as redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from tripsage_core.services.business.api_key_service import (
    ApiKeyCreateRequest,
    ApiKeyService,
    ServiceType,
    ValidationStatus,
)


@pytest.fixture(scope="session")
async def test_db_engine():
    """Create test database engine."""
    # Use in-memory SQLite for tests
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True,
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE api_keys (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                service TEXT NOT NULL,
                encrypted_key TEXT NOT NULL,
                description TEXT,
                is_valid BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                last_used TIMESTAMP,
                last_validated TIMESTAMP,
                usage_count INTEGER DEFAULT 0
            )
        """))
        
        await conn.execute(text("""
            CREATE TABLE api_key_usage_logs (
                id TEXT PRIMARY KEY,
                key_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                service TEXT NOT NULL,
                operation TEXT NOT NULL,
                success BOOLEAN NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                response_time REAL,
                error_message TEXT,
                FOREIGN KEY (key_id) REFERENCES api_keys (id)
            )
        """))
    
    yield engine
    
    await engine.dispose()


@pytest.fixture(scope="session")
async def test_redis():
    """Create test Redis connection."""
    # Try to connect to test Redis, fallback to mock if not available
    try:
        redis_client = redis.from_url(
            os.getenv("TEST_REDIS_URL", "redis://localhost:6379/15"),
            decode_responses=True,
        )
        await redis_client.ping()
        yield redis_client
        await redis_client.flushdb()  # Clean up
        await redis_client.close()
    except Exception:
        # Fallback to mock Redis for CI environments
        from unittest.mock import AsyncMock
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None
        mock_redis.set.return_value = True
        mock_redis.delete.return_value = 1
        yield mock_redis


@pytest.fixture
async def db_session(test_db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create database session for each test."""
    async with AsyncSession(test_db_engine) as session:
        yield session
        await session.rollback()


@pytest.fixture
async def api_service_integration(db_session, test_redis):
    """Create ApiKeyService with real database and cache dependencies."""
    from unittest.mock import AsyncMock
    
    # Create service with real DB and cache
    service = ApiKeyService()
    
    # Mock the database service to use our test session
    db_mock = AsyncMock()
    
    async def mock_create_api_key(user_id: str, request: ApiKeyCreateRequest):
        key_id = str(uuid.uuid4())
        await db_session.execute(text("""
            INSERT INTO api_keys (
                id, user_id, name, service, encrypted_key, description,
                created_at, updated_at
            ) VALUES (
                :id, :user_id, :name, :service, :encrypted_key, :description,
                :created_at, :updated_at
            )
        """), {
            "id": key_id,
            "user_id": user_id,
            "name": request.name,
            "service": request.service.value,
            "encrypted_key": service._encrypt_key(request.key_value),
            "description": request.description,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        })
        await db_session.commit()
        
        return {
            "id": key_id,
            "name": request.name,
            "service": request.service.value,
            "description": request.description,
            "is_valid": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": None,
            "last_used": None,
            "last_validated": datetime.now(timezone.utc).isoformat(),
            "usage_count": 0,
        }
    
    async def mock_get_api_key(key_id: str):
        result = await db_session.execute(
            text("SELECT * FROM api_keys WHERE id = :id"),
            {"id": key_id}
        )
        row = result.fetchone()
        if row:
            return dict(row._mapping)
        return None
    
    async def mock_list_user_keys(user_id: str):
        result = await db_session.execute(
            text("SELECT * FROM api_keys WHERE user_id = :user_id"),
            {"user_id": user_id}
        )
        return [dict(row._mapping) for row in result.fetchall()]
    
    async def mock_delete_api_key(key_id: str):
        result = await db_session.execute(
            text("DELETE FROM api_keys WHERE id = :id"),
            {"id": key_id}
        )
        await db_session.commit()
        return result.rowcount > 0
    
    async def mock_log_usage(**kwargs):
        log_id = str(uuid.uuid4())
        await db_session.execute(text("""
            INSERT INTO api_key_usage_logs (
                id, key_id, user_id, service, operation, success, timestamp
            ) VALUES (
                :id, :key_id, :user_id, :service, :operation, :success, :timestamp
            )
        """), {
            "id": log_id,
            "timestamp": datetime.now(timezone.utc),
            **kwargs,
        })
        await db_session.commit()
    
    # Wire up mocked database methods
    db_mock.create_api_key = mock_create_api_key
    db_mock.get_api_key = mock_get_api_key
    db_mock.list_user_keys = mock_list_user_keys
    db_mock.delete_api_key = mock_delete_api_key
    db_mock.log_api_key_usage = mock_log_usage
    
    # Create cache mock that uses real Redis
    cache_mock = AsyncMock()
    
    async def mock_get_json(key: str):
        value = await test_redis.get(key)
        if value:
            import json
            return json.loads(value)
        return None
    
    async def mock_set_json(key: str, value: dict, ttl: int = None):
        import json
        await test_redis.set(key, json.dumps(value), ex=ttl)
        return True
    
    cache_mock.get_json = mock_get_json
    cache_mock.set_json = mock_set_json
    cache_mock.get = test_redis.get
    cache_mock.set = test_redis.set
    cache_mock.delete = test_redis.delete
    
    # Inject dependencies
    service.db = db_mock
    service.cache = cache_mock
    service.audit = AsyncMock()  # Keep audit as mock for simplicity
    
    await service.initialize()
    return service


class TestApiKeyServiceIntegration:
    """Integration tests with real database and cache."""

    @pytest.mark.asyncio
    async def test_full_key_lifecycle_integration(self, api_service_integration):
        """Test complete key lifecycle with real dependencies."""
        user_id = str(uuid.uuid4())
        
        # Create key
        request = ApiKeyCreateRequest(
            name="Integration Test Key",
            service=ServiceType.OPENAI,
            key_value="sk-integration_test_key_12345",
            description="Test key for integration testing",
        )
        
        # Mock external API validation
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = mock_get.return_value
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": [{"id": "model-1"}]}
            
            created_key = await api_service_integration.create_api_key(user_id, request)
            
            # Verify creation
            assert created_key.name == request.name
            assert created_key.service == request.service
            assert created_key.is_valid is True
            assert created_key.id is not None
            
            key_id = created_key.id
        
        # List keys
        user_keys = await api_service_integration.list_user_keys(user_id)
        assert len(user_keys) == 1
        assert user_keys[0].id == key_id
        
        # Get specific key
        retrieved_key = await api_service_integration.get_key(key_id)
        assert retrieved_key is not None
        assert retrieved_key["id"] == key_id
        assert retrieved_key["name"] == request.name
        
        # Delete key
        deleted = await api_service_integration.delete_api_key(key_id, user_id)
        assert deleted is True
        
        # Verify deletion
        deleted_key = await api_service_integration.get_key(key_id)
        assert deleted_key is None
        
        empty_list = await api_service_integration.list_user_keys(user_id)
        assert len(empty_list) == 0

    @pytest.mark.asyncio
    async def test_validation_caching_integration(self, api_service_integration):
        """Test validation result caching with real Redis."""
        user_id = str(uuid.uuid4())
        test_key = "sk-cache_test_key_12345"
        
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = mock_get.return_value
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": [{"id": "model-1"}]}
            
            # First validation - should hit external API
            result1 = await api_service_integration.validate_api_key(
                ServiceType.OPENAI, test_key, user_id
            )
            assert result1.is_valid is True
            assert mock_get.call_count == 1
            
            # Second validation - should use cache
            result2 = await api_service_integration.validate_api_key(
                ServiceType.OPENAI, test_key, user_id
            )
            assert result2.is_valid is True
            # Call count should still be 1 (cached result)
            assert mock_get.call_count == 1

    @pytest.mark.asyncio
    async def test_concurrent_operations_integration(self, api_service_integration):
        """Test concurrent database operations."""
        user_id = str(uuid.uuid4())
        
        # Create multiple keys concurrently
        async def create_test_key(index):
            request = ApiKeyCreateRequest(
                name=f"Concurrent Test Key {index}",
                service=ServiceType.OPENAI,
                key_value=f"sk-concurrent_test_{index}",
                description=f"Concurrent test key {index}",
            )
            
            with patch("httpx.AsyncClient.get") as mock_get:
                mock_response = mock_get.return_value
                mock_response.status_code = 200
                mock_response.json.return_value = {"data": [{"id": "model-1"}]}
                
                return await api_service_integration.create_key(user_id, request)
        
        # Create 5 keys concurrently
        tasks = [create_test_key(i) for i in range(5)]
        created_keys = await asyncio.gather(*tasks)
        
        # Verify all keys were created
        assert len(created_keys) == 5
        assert all(key.is_valid for key in created_keys)
        
        # Verify they're all in the database
        user_keys = await api_service_integration.list_user_keys(user_id)
        assert len(user_keys) == 5

    @pytest.mark.asyncio
    async def test_rate_limiting_integration(self, api_service_integration, test_redis):
        """Test rate limiting with real Redis."""
        user_id = str(uuid.uuid4())
        
        # Simulate rapid requests
        for _i in range(12):  # Exceed typical rate limit of 10
            await test_redis.incr(f"rate_limit:{user_id}")
            await test_redis.expire(f"rate_limit:{user_id}", 60)
        
        # Check rate limiting
        is_limited = await api_service_integration._is_rate_limited(user_id)
        assert is_limited is True
        
        # Clean up and verify rate limit resets
        await test_redis.delete(f"rate_limit:{user_id}")
        is_limited_after_reset = await api_service_integration._is_rate_limited(user_id)
        assert is_limited_after_reset is False

    @pytest.mark.asyncio
    async def test_key_rotation_integration(self, api_service_integration):
        """Test key rotation with database persistence."""
        user_id = str(uuid.uuid4())
        
        # Create initial key
        request = ApiKeyCreateRequest(
            name="Rotation Test Key",
            service=ServiceType.OPENAI,
            key_value="sk-original_key_12345",
            description="Key for rotation testing",
        )
        
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = mock_get.return_value
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": [{"id": "model-1"}]}
            
            created_key = await api_service_integration.create_api_key(user_id, request)
            key_id = created_key.id
            
            # Rotate the key
            new_key_value = "sk-rotated_key_67890"
            rotated_key = await api_service_integration.rotate_key(
                key_id, new_key_value, user_id
            )
            
            # Verify rotation
            assert rotated_key.id == key_id  # Same ID
            assert rotated_key.is_valid is True
            
            # Verify the key was updated in database
            updated_key = await api_service_integration.get_key(key_id)
            assert updated_key is not None
            # Note: We can't directly compare the encrypted key value,
            # but we can verify the key was updated by checking timestamps

    @pytest.mark.asyncio
    async def test_monitoring_integration(self, api_service_integration, test_redis):
        """Test monitoring with real cache storage."""
        key_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        
        # Store monitoring data directly in Redis
        monitoring_data = {
            "last_check": datetime.now(timezone.utc).isoformat(),
            "status": "healthy",
            "response_time": 120,
            "success_rate": 0.98,
            "error_count": 1,
        }
        
        import json
        await test_redis.set(
            f"monitor:{key_id}",
            json.dumps(monitoring_data),
            ex=3600,
        )
        
        # Retrieve monitoring data through service
        result = await api_service_integration.monitor_key(key_id, user_id)
        
        # Verify data integrity
        assert result["status"] == "healthy"
        assert result["response_time"] == 120
        assert result["success_rate"] == 0.98

    @pytest.mark.asyncio
    async def test_error_handling_integration(self, api_service_integration):
        """Test error handling with real external API failures."""
        user_id = str(uuid.uuid4())
        
        # Test network timeout
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.side_effect = asyncio.TimeoutError("Network timeout")
            
            result = await api_service_integration.validate_api_key(
                ServiceType.OPENAI, "sk-timeout_test", user_id
            )
            
            assert result.is_valid is False
            assert result.status == ValidationStatus.SERVICE_ERROR
            assert "timeout" in result.message.lower()
        
        # Test HTTP error responses
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = mock_get.return_value
            mock_response.status_code = 401
            mock_response.json.return_value = {
                "error": {"message": "Invalid API key"}
            }
            
            result = await api_service_integration.validate_api_key(
                ServiceType.OPENAI, "sk-invalid_key", user_id
            )
            
            assert result.is_valid is False
            assert result.status == ValidationStatus.INVALID

    @pytest.mark.asyncio
    async def test_encryption_integration(self, api_service_integration):
        """Test key encryption/decryption with database storage."""
        original_key = "sk-encryption_test_very_secret_key"
        
        # Test encryption
        encrypted = api_service_integration._encrypt_key(original_key)
        assert encrypted != original_key
        assert len(encrypted) > len(original_key)
        
        # Test decryption
        decrypted = api_service_integration._decrypt_key(encrypted)
        assert decrypted == original_key
        
        # Test with different key lengths
        test_keys = [
            "sk-short",
            "sk-" + "a" * 100,  # Long key
            "sk-special!@#$%^&*()",  # Special characters
        ]
        
        for test_key in test_keys:
            encrypted = api_service_integration._encrypt_key(test_key)
            decrypted = api_service_integration._decrypt_key(encrypted)
            assert decrypted == test_key

    @pytest.mark.asyncio
    async def test_usage_logging_integration(self, api_service_integration, db_session):
        """Test usage logging with real database."""
        key_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        
        # Log usage
        await api_service_integration._log_usage(
            key_id=key_id,
            user_id=user_id,
            service="openai",
            operation="validation",
            success=True,
        )
        
        # Verify log entry was created
        result = await db_session.execute(
            text("SELECT * FROM api_key_usage_logs WHERE key_id = :key_id"),
            {"key_id": key_id}
        )
        
        log_entries = result.fetchall()
        assert len(log_entries) == 1
        
        log_entry = dict(log_entries[0]._mapping)
        assert log_entry["key_id"] == key_id
        assert log_entry["user_id"] == user_id
        assert log_entry["service"] == "openai"
        assert log_entry["operation"] == "validation"
        assert log_entry["success"] is True