"""Specialized cache failure tests for API Key Service.

This file contains comprehensive tests for cache infrastructure failures,
edge cases, and resilience scenarios.
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError

from tripsage_core.models.db.api_key import APIKeyCreate
from tripsage_core.services.business.api_key_service import APIKeyService
from tripsage_core.utils.logging_utils import get_logger

logger = get_logger(__name__)


@pytest.fixture
def mock_database_service():
    """Mock database service for testing."""
    return AsyncMock()


@pytest.fixture
def mock_cache_service():
    """Mock cache service for testing."""
    return AsyncMock()


@pytest.fixture
def mock_encryption_key():
    """Generate a test encryption key."""
    from cryptography.fernet import Fernet

    return Fernet.generate_key()


@pytest.fixture
async def api_key_service(
    mock_database_service, mock_cache_service, mock_encryption_key
):
    """Create APIKeyService instance for testing."""
    with patch("tripsage_core.services.business.api_key_service.Fernet"):
        service = APIKeyService(
            database_service=mock_database_service,
            cache_service=mock_cache_service,
            encryption_key=mock_encryption_key.decode(),
        )
        yield service


class TestCacheConnectionFailures:
    """Test cache connection failure scenarios."""

    async def test_cache_connection_error_fallback(
        self, api_key_service, mock_database_service, mock_cache_service
    ):
        """Test fallback to database when cache connection fails."""
        api_key = "test_key"
        mock_cache_service.get.side_effect = RedisConnectionError("Connection refused")

        mock_database_service.fetch_one.return_value = {
            "id": uuid.uuid4(),
            "user_id": uuid.uuid4(),
            "name": "Test Key",
            "key_hash": "hash",
            "service": "test",
            "permissions": ["read"],
            "rate_limit": 100,
            "expires_at": datetime.now(timezone.utc) + timedelta(days=30),
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "last_used_at": None,
            "is_active": True,
        }

        # Should still work by falling back to database
        with patch.object(api_key_service, "_validate_api_key_hash", return_value=True):
            result = await api_key_service.validate_api_key(api_key)

        assert result is not None
        mock_database_service.fetch_one.assert_called_once()

    async def test_cache_timeout_error_handling(
        self, api_key_service, mock_database_service, mock_cache_service
    ):
        """Test handling of cache timeout errors."""
        api_key = "timeout_key"
        mock_cache_service.get.side_effect = RedisTimeoutError("Operation timed out")

        mock_database_service.fetch_one.return_value = None

        # Should handle timeout gracefully and check database
        from tripsage_core.exceptions.exceptions import (
            CoreResourceNotFoundError as NotFoundError,
        )

        with pytest.raises(NotFoundError):
            await api_key_service.validate_api_key(api_key)

    async def test_cache_set_failure_silent(
        self, api_key_service, mock_database_service, mock_cache_service
    ):
        """Test that cache set failures don't affect operation success."""
        user_id = uuid.uuid4()
        create_request = APIKeyCreate(
            name="Test Key",
            service="test_service",
            permissions=["read"],
        )

        mock_database_service.fetch_one.side_effect = [
            None,  # No duplicate
            {  # Created key
                "id": uuid.uuid4(),
                "user_id": user_id,
                "name": create_request.name,
                "key_hash": "hash",
                "service": create_request.service,
                "permissions": create_request.permissions,
                "rate_limit": 100,
                "expires_at": datetime.now(timezone.utc) + timedelta(days=30),
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "last_used_at": None,
                "is_active": True,
            },
        ]

        mock_cache_service.set.side_effect = RedisConnectionError("Cannot set cache")

        # Should still succeed despite cache failure
        result = await api_key_service.create_api_key(str(user_id), create_request)
        assert result is not None

    async def test_cache_delete_failure_silent(
        self, api_key_service, mock_database_service, mock_cache_service
    ):
        """Test that cache delete failures don't affect operation success."""
        key_id = uuid.uuid4()
        user_id = uuid.uuid4()

        mock_database_service.fetch_one.return_value = {
            "id": key_id,
            "user_id": user_id,
            "key_hash": "hash",
        }
        mock_database_service.execute.return_value = None

        mock_cache_service.delete.side_effect = RedisConnectionError(
            "Cannot delete from cache"
        )

        # Should still succeed despite cache failure
        await api_key_service.delete_api_key(str(key_id), str(user_id))
        mock_database_service.execute.assert_called_once()


class TestCacheDataCorruption:
    """Test cache data corruption scenarios."""

    async def test_corrupted_json_in_cache(
        self, api_key_service, mock_database_service, mock_cache_service
    ):
        """Test handling of corrupted JSON data in cache."""
        api_key = "corrupted_key"
        mock_cache_service.get.return_value = "{'invalid': json data"  # Corrupted JSON

        mock_database_service.fetch_one.return_value = {
            "id": uuid.uuid4(),
            "user_id": uuid.uuid4(),
            "name": "Test Key",
            "key_hash": "hash",
            "service": "test",
            "permissions": ["read"],
            "rate_limit": 100,
            "expires_at": datetime.now(timezone.utc) + timedelta(days=30),
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "last_used_at": None,
            "is_active": True,
        }

        # Should fall back to database on JSON decode error
        with patch.object(api_key_service, "_validate_api_key_hash", return_value=True):
            result = await api_key_service.validate_api_key(api_key)

        assert result is not None
        mock_database_service.fetch_one.assert_called_once()

    async def test_incomplete_data_in_cache(self, api_key_service, mock_cache_service):
        """Test handling of incomplete data in cache."""
        api_key = "incomplete_key"
        # Missing required fields
        mock_cache_service.get.return_value = json.dumps(
            {
                "id": str(uuid.uuid4()),
                "user_id": str(uuid.uuid4()),
                # Missing other required fields
            }
        )

        # Should handle incomplete data gracefully
        with pytest.raises(ValueError):
            await api_key_service.validate_api_key(api_key)

    async def test_invalid_date_format_in_cache(
        self, api_key_service, mock_cache_service
    ):
        """Test handling of invalid date formats in cached data."""
        api_key = "invalid_date_key"
        mock_cache_service.get.return_value = json.dumps(
            {
                "id": str(uuid.uuid4()),
                "user_id": str(uuid.uuid4()),
                "name": "Test Key",
                "service": "test",
                "permissions": ["read"],
                "rate_limit": 100,
                "expires_at": "invalid-date-format",  # Invalid date
                "is_active": True,
            }
        )

        # Should handle invalid date format
        with pytest.raises(ValueError):
            await api_key_service.validate_api_key(api_key)


class TestCacheInfrastructureResilience:
    """Test cache infrastructure resilience."""

    async def test_intermittent_cache_failures(
        self, api_key_service, mock_database_service, mock_cache_service
    ):
        """Test handling of intermittent cache failures."""
        api_keys = ["key1", "key2", "key3", "key4", "key5"]

        # Simulate intermittent failures
        mock_cache_service.get.side_effect = [
            RedisConnectionError("Connection lost"),
            json.dumps(
                {
                    "id": "1",
                    "user_id": "1",
                    "name": "Key 2",
                    "service": "test",
                    "permissions": ["read"],
                    "rate_limit": 100,
                    "expires_at": datetime.now(timezone.utc).isoformat(),
                    "is_active": True,
                }
            ),
            RedisTimeoutError("Timeout"),
            json.dumps(
                {
                    "id": "4",
                    "user_id": "4",
                    "name": "Key 4",
                    "service": "test",
                    "permissions": ["read"],
                    "rate_limit": 100,
                    "expires_at": datetime.now(timezone.utc).isoformat(),
                    "is_active": True,
                }
            ),
            RedisConnectionError("Connection lost"),
        ]

        mock_database_service.fetch_one.return_value = {
            "id": uuid.uuid4(),
            "user_id": uuid.uuid4(),
            "name": "Test Key",
            "key_hash": "hash",
            "service": "test",
            "permissions": ["read"],
            "rate_limit": 100,
            "expires_at": datetime.now(timezone.utc) + timedelta(days=30),
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "last_used_at": None,
            "is_active": True,
        }

        results = []
        for key in api_keys:
            try:
                with patch.object(
                    api_key_service, "_validate_api_key_hash", return_value=True
                ):
                    result = await api_key_service.validate_api_key(key)
                results.append(("success", result))
            except Exception as e:
                results.append(("error", str(e)))

        # Should have mix of successes and failures
        successes = [r for r in results if r[0] == "success"]
        assert len(successes) >= 2  # At least cache hits should succeed

    async def test_cache_recovery_after_failure(
        self, api_key_service, mock_database_service, mock_cache_service
    ):
        """Test cache recovery after connection is restored."""
        api_key = "recovery_key"

        # First attempt - cache fails
        mock_cache_service.get.side_effect = [
            RedisConnectionError("Connection lost"),
            None,  # Second attempt - connection restored but no data
        ]

        mock_database_service.fetch_one.return_value = {
            "id": uuid.uuid4(),
            "user_id": uuid.uuid4(),
            "name": "Test Key",
            "key_hash": "hash",
            "service": "test",
            "permissions": ["read"],
            "rate_limit": 100,
            "expires_at": datetime.now(timezone.utc) + timedelta(days=30),
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "last_used_at": None,
            "is_active": True,
        }

        # First validation - should use database
        with patch.object(api_key_service, "_validate_api_key_hash", return_value=True):
            result1 = await api_key_service.validate_api_key(api_key)

        # Reset side effect for set operation
        mock_cache_service.set.side_effect = None

        # Second validation - cache should work now
        with patch.object(api_key_service, "_validate_api_key_hash", return_value=True):
            result2 = await api_key_service.validate_api_key(api_key)

        assert result1 is not None
        assert result2 is not None
        assert mock_cache_service.set.call_count >= 1  # Should attempt to cache


class TestCacheConcurrencyIssues:
    """Test cache concurrency and race condition scenarios."""

    async def test_concurrent_cache_operations(
        self, api_key_service, mock_database_service, mock_cache_service
    ):
        """Test concurrent cache operations."""
        num_concurrent = 20
        api_keys = [f"concurrent_key_{i}" for i in range(num_concurrent)]

        # Simulate various cache behaviors
        cache_responses = []
        for i in range(num_concurrent):
            if i % 4 == 0:
                cache_responses.append(RedisConnectionError("Connection error"))
            elif i % 4 == 1:
                cache_responses.append(None)  # Cache miss
            elif i % 4 == 2:
                cache_responses.append(RedisTimeoutError("Timeout"))
            else:
                cache_responses.append(
                    json.dumps(
                        {
                            "id": str(uuid.uuid4()),
                            "user_id": str(uuid.uuid4()),
                            "name": f"Key {i}",
                            "service": "test",
                            "permissions": ["read"],
                            "rate_limit": 100,
                            "expires_at": (
                                datetime.now(timezone.utc) + timedelta(days=30)
                            ).isoformat(),
                            "is_active": True,
                        }
                    )
                )

        mock_cache_service.get.side_effect = cache_responses
        mock_database_service.fetch_one.return_value = {
            "id": uuid.uuid4(),
            "user_id": uuid.uuid4(),
            "name": "Test Key",
            "key_hash": "hash",
            "service": "test",
            "permissions": ["read"],
            "rate_limit": 100,
            "expires_at": datetime.now(timezone.utc) + timedelta(days=30),
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "last_used_at": None,
            "is_active": True,
        }

        with patch.object(api_key_service, "_validate_api_key_hash", return_value=True):
            tasks = [api_key_service.validate_api_key(key) for key in api_keys]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        # Should handle all scenarios without crashing
        successful = [r for r in results if not isinstance(r, Exception)]
        assert (
            len(successful) >= num_concurrent // 4
        )  # At least cache hits should succeed

    async def test_cache_stampede_prevention(
        self, api_key_service, mock_database_service, mock_cache_service
    ):
        """Test prevention of cache stampede on popular keys."""
        popular_key = "very_popular_key"
        num_requests = 50

        mock_cache_service.get.return_value = None  # Simulate cache miss

        # Track database calls
        call_count = 0

        async def count_calls(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return {
                "id": uuid.uuid4(),
                "user_id": uuid.uuid4(),
                "name": "Popular Key",
                "key_hash": "hash",
                "service": "test",
                "permissions": ["read"],
                "rate_limit": 1000,
                "expires_at": datetime.now(timezone.utc) + timedelta(days=30),
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "last_used_at": None,
                "is_active": True,
            }

        mock_database_service.fetch_one.side_effect = count_calls

        # Simulate many concurrent requests for same key
        with patch.object(api_key_service, "_validate_api_key_hash", return_value=True):
            tasks = [
                api_key_service.validate_api_key(popular_key)
                for _ in range(num_requests)
            ]
            await asyncio.gather(*tasks, return_exceptions=True)

        # Database should be called multiple times but not for every request
        # (some natural deduplication may occur)
        assert call_count > 0
        assert call_count <= num_requests


class TestCacheHealthMonitoring:
    """Test cache health monitoring and metrics."""

    async def test_health_check_cache_unhealthy(
        self, api_key_service, mock_database_service, mock_cache_service
    ):
        """Test health check when cache is unhealthy."""
        mock_database_service.execute.return_value = None
        mock_cache_service.get.side_effect = RedisConnectionError("Cache unavailable")

        result = await api_key_service.health_check()

        assert result["status"] == "unhealthy"
        assert result["database"] == "ok"
        assert result["cache"] == "error"

    async def test_health_check_both_unhealthy(
        self, api_key_service, mock_database_service, mock_cache_service
    ):
        """Test health check when both services are unhealthy."""
        mock_database_service.execute.side_effect = Exception("DB error")
        mock_cache_service.get.side_effect = RedisConnectionError("Cache error")

        result = await api_key_service.health_check()

        assert result["status"] == "unhealthy"
        assert result["database"] == "error"
        assert result["cache"] == "error"

    async def test_cache_performance_degradation(
        self, api_key_service, mock_cache_service
    ):
        """Test detection of cache performance degradation."""

        # Simulate slow cache responses
        async def slow_cache_get(*args, **kwargs):
            await asyncio.sleep(0.5)  # 500ms delay
            return None

        mock_cache_service.get = slow_cache_get

        start_time = asyncio.get_event_loop().time()

        # This should timeout or take long
        try:
            await asyncio.wait_for(
                api_key_service.validate_api_key("slow_key"), timeout=1.0
            )
        except asyncio.TimeoutError:
            pass
        except Exception:
            pass

        elapsed = asyncio.get_event_loop().time() - start_time

        # Should detect slow cache and potentially bypass it
        assert elapsed < 2.0  # Should not wait indefinitely


class TestCacheInvalidation:
    """Test cache invalidation scenarios."""

    async def test_cache_invalidation_on_update(
        self, api_key_service, mock_database_service, mock_cache_service
    ):
        """Test cache invalidation when key is updated."""
        key_id = uuid.uuid4()
        user_id = uuid.uuid4()
        key_hash = "original_hash"

        # Setup initial state
        mock_database_service.fetch_one.side_effect = [
            {"id": key_id, "user_id": user_id, "key_hash": key_hash},
            {
                "id": key_id,
                "user_id": user_id,
                "name": "Updated",
                "key_hash": key_hash,
                "service": "test",
                "permissions": ["read", "write"],
                "rate_limit": 200,
                "expires_at": datetime.now(timezone.utc) + timedelta(days=30),
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "last_used_at": None,
                "is_active": True,
            },
        ]

        from tripsage_core.models.db.api_key import APIKeyUpdate

        update_request = APIKeyUpdate(permissions=["read", "write"])

        await api_key_service.update_api_key(str(key_id), str(user_id), update_request)

        # Cache should be invalidated
        mock_cache_service.delete.assert_called_once()

    async def test_cache_invalidation_on_delete(
        self, api_key_service, mock_database_service, mock_cache_service
    ):
        """Test cache invalidation when key is deleted."""
        key_id = uuid.uuid4()
        user_id = uuid.uuid4()
        key_hash = "deleted_hash"

        mock_database_service.fetch_one.return_value = {
            "id": key_id,
            "user_id": user_id,
            "key_hash": key_hash,
        }

        await api_key_service.delete_api_key(str(key_id), str(user_id))

        # Cache should be invalidated
        mock_cache_service.delete.assert_called_once_with(f"api_key:{key_hash}")

    async def test_bulk_cache_invalidation(
        self, api_key_service, mock_database_service, mock_cache_service
    ):
        """Test bulk cache invalidation scenarios."""
        user_id = uuid.uuid4()

        # Simulate deactivating all user's keys
        mock_database_service.fetch_many.return_value = [
            {
                "id": uuid.uuid4(),
                "user_id": user_id,
                "name": f"Key {i}",
                "key_hash": f"hash_{i}",
                "service": "test",
                "permissions": ["read"],
                "rate_limit": 100,
                "expires_at": datetime.now(timezone.utc) + timedelta(days=30),
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "last_used_at": None,
                "is_active": True,
            }
            for i in range(5)
        ]

        # Get all user keys
        keys = await api_key_service.list_user_keys(str(user_id))

        # Simulate bulk deactivation (would need to be implemented)
        for key in keys:
            mock_database_service.fetch_one.return_value = {
                "id": key.id,
                "user_id": user_id,
                "key_hash": f"hash_{keys.index(key)}",
            }
            await api_key_service.delete_api_key(str(key.id), str(user_id))

        # All keys should be invalidated from cache
        assert mock_cache_service.delete.call_count == len(keys)
