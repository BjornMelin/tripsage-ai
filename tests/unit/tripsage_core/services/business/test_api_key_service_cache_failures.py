"""
Comprehensive cache infrastructure failure tests for API key service.

This module provides extensive testing of cache failure scenarios to ensure
the service maintains resilience when DragonflyDB/Redis cache is unavailable,
times out, or encounters errors. Tests target lines 1128-1159 in api_key_service.py.

Key failure modes tested:
- Cache connection failures (ConnectionError, TimeoutError)
- Cache operation timeouts
- JSON serialization/deserialization errors
- Cache service unavailable scenarios
- Redis client exceptions
- Graceful degradation without cache
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest
import redis.exceptions

from tripsage_core.services.business.api_key_service import (
    ApiKeyService,
    ServiceType,
    ValidationResult,
    ValidationStatus,
)


class TestApiKeyServiceCacheFailures:
    """Comprehensive cache infrastructure failure tests."""

    @pytest.fixture
    async def mock_dependencies(self):
        """Create mocked dependencies with proper cache interface."""
        db = AsyncMock()
        cache = AsyncMock()

        # Set up realistic database responses
        db.create_api_key.return_value = {
            "id": str(uuid.uuid4()),
            "name": "Test API Key",
            "service": "openai",
            "description": "Test description",
            "is_valid": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": None,
            "last_used": None,
            "last_validated": datetime.now(timezone.utc).isoformat(),
            "usage_count": 0,
        }

        return {"db": db, "cache": cache}

    @pytest.fixture
    async def api_service(self, mock_dependencies):
        """Create API key service with mocked dependencies."""
        return ApiKeyService(
            db=mock_dependencies["db"],
            cache=mock_dependencies["cache"],
            validation_timeout=10,
        )

    # Cache Connection Failures (Lines 1135-1136, 1159-1160)

    @pytest.mark.asyncio
    async def test_cache_none_graceful_degradation(self, mock_dependencies):
        """Test service works gracefully when cache service is None."""
        # Create service without cache
        service = ApiKeyService(db=mock_dependencies["db"], cache=None)
        user_id = str(uuid.uuid4())

        with patch.object(service.client, "get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": [{"id": "model-1"}]}
            mock_get.return_value = mock_response

            # Should work without cache
            result = await service.validate_api_key(
                ServiceType.OPENAI, "sk-test-key-12345", user_id
            )

            assert result.is_valid is True
            assert result.status == ValidationStatus.VALID
            # Ensure no cache calls were made
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_connection_error_during_get(
        self, api_service, mock_dependencies
    ):
        """Test cache retrieval when connection fails - targets line 1145."""
        user_id = str(uuid.uuid4())

        # Mock cache get to raise ConnectionError
        mock_dependencies["cache"].get.side_effect = redis.exceptions.ConnectionError(
            "Connection to Redis failed"
        )

        with patch.object(api_service.client, "get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": [{"id": "model-1"}]}
            mock_get.return_value = mock_response

            # Should fallback to actual validation
            result = await api_service.validate_api_key(
                ServiceType.OPENAI, "sk-test-key-12345", user_id
            )

            assert result.is_valid is True
            assert result.status == ValidationStatus.VALID
            # Verify cache was attempted but fallback occurred
            mock_dependencies["cache"].get.assert_called_once()
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_timeout_error_during_get(self, api_service, mock_dependencies):
        """Test cache retrieval timeout handling - targets line 1150."""
        user_id = str(uuid.uuid4())

        # Mock cache get to raise TimeoutError
        mock_dependencies["cache"].get.side_effect = redis.exceptions.TimeoutError(
            "Cache operation timed out"
        )

        with patch.object(api_service.client, "get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "main": {"temp": 20}
            }  # Weather API response format
            mock_response.headers = {}  # Empty headers
            mock_get.return_value = mock_response

            # Should continue validation despite timeout - use valid weather key format
            result = await api_service.validate_api_key(
                ServiceType.WEATHER, "valid-weather-key-16-chars", user_id
            )

            assert result.is_valid is True
            assert result.status == ValidationStatus.VALID

    # Cache Operation Errors (Lines 1145-1151)

    @pytest.mark.asyncio
    async def test_cache_json_decode_error(self, api_service, mock_dependencies):
        """Test handling of corrupted JSON data in cache - targets line 1147."""
        user_id = str(uuid.uuid4())

        # Mock cache to return invalid JSON
        mock_dependencies["cache"].get.return_value = "{invalid json data"

        with patch.object(api_service.client, "get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": [{"id": "model-1"}]}
            mock_get.return_value = mock_response

            # Should handle JSON decode error gracefully
            result = await api_service.validate_api_key(
                ServiceType.OPENAI, "sk-test-key-12345", user_id
            )

            assert result.is_valid is True
            # Should fall back to actual validation when cache is corrupted
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_validation_result_construction_error(
        self, api_service, mock_dependencies
    ):
        """Test handling of ValidationResult construction errors - targets line 1148."""
        user_id = str(uuid.uuid4())

        # Mock cache to return valid JSON but invalid ValidationResult data
        invalid_data = {"invalid_field": "value", "status": "unknown_status"}
        mock_dependencies["cache"].get.return_value = json.dumps(invalid_data)

        with patch.object(api_service.client, "get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": [{"id": "model-1"}]}
            mock_get.return_value = mock_response

            # Should handle ValidationResult construction error gracefully
            result = await api_service.validate_api_key(
                ServiceType.OPENAI, "sk-test-key-12345", user_id
            )

            assert result.is_valid is True
            # Should fall back to actual validation
            mock_get.assert_called_once()

    # Cache Storage Failures (Lines 1162-1176)

    @pytest.mark.asyncio
    async def test_cache_storage_connection_error(self, api_service, mock_dependencies):
        """Test cache storage when connection fails - targets line 1169."""
        user_id = str(uuid.uuid4())

        # Mock cache get to return None (no cached result)
        mock_dependencies["cache"].get.return_value = None
        # Mock cache set to raise ConnectionError
        mock_dependencies["cache"].set.side_effect = redis.exceptions.ConnectionError(
            "Connection to Redis failed during write"
        )

        with patch.object(api_service.client, "get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": [{"id": "model-1"}]}
            mock_get.return_value = mock_response

            # Should validate successfully despite cache write failure
            result = await api_service.validate_api_key(
                ServiceType.OPENAI, "sk-test-key-12345", user_id
            )

            assert result.is_valid is True
            assert result.status == ValidationStatus.VALID
            # Verify cache write was attempted
            mock_dependencies["cache"].set.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_storage_timeout_error(self, api_service, mock_dependencies):
        """Test cache storage timeout handling - targets line 1175."""
        user_id = str(uuid.uuid4())

        # Mock cache operations
        mock_dependencies["cache"].get.return_value = None
        mock_dependencies["cache"].set.side_effect = redis.exceptions.TimeoutError(
            "Cache write operation timed out"
        )

        with patch.object(api_service.client, "get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "status": "OK",
                "results": [],
            }  # Google Maps API response
            mock_get.return_value = mock_response

            # Should complete validation despite cache timeout - use valid Maps key
            result = await api_service.validate_api_key(
                ServiceType.GOOGLEMAPS, "valid-googlemaps-key-20chars-minimum", user_id
            )

            assert result.is_valid is True
            assert result.status == ValidationStatus.VALID

    @pytest.mark.asyncio
    async def test_cache_json_serialization_error(self, api_service, mock_dependencies):
        """Test handling of JSON serialization errors during cache write."""
        user_id = str(uuid.uuid4())

        mock_dependencies["cache"].get.return_value = None

        with (
            patch.object(api_service.client, "get") as mock_get,
            patch("json.dumps", side_effect=TypeError("Object not JSON serializable")),
        ):
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": [{"id": "model-1"}]}
            mock_get.return_value = mock_response

            # Should complete validation despite serialization error
            result = await api_service.validate_api_key(
                ServiceType.OPENAI, "sk-test-key-12345", user_id
            )

            assert result.is_valid is True
            assert result.status == ValidationStatus.VALID

    # Redis Client Specific Failures

    @pytest.mark.asyncio
    async def test_redis_response_error_during_get(
        self, api_service, mock_dependencies
    ):
        """Test handling of Redis response errors."""
        user_id = str(uuid.uuid4())

        # Mock cache get to raise ResponseError
        mock_dependencies["cache"].get.side_effect = redis.exceptions.ResponseError(
            "Redis server returned an error"
        )

        with patch.object(api_service.client, "get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": [{"id": "model-1"}]}
            mock_get.return_value = mock_response

            # Should handle Redis error gracefully
            result = await api_service.validate_api_key(
                ServiceType.OPENAI, "sk-test-key-12345", user_id
            )

            assert result.is_valid is True
            assert result.status == ValidationStatus.VALID

    @pytest.mark.asyncio
    async def test_redis_data_error_during_set(self, api_service, mock_dependencies):
        """Test handling of Redis data errors during cache write."""
        user_id = str(uuid.uuid4())

        mock_dependencies["cache"].get.return_value = None
        mock_dependencies["cache"].set.side_effect = redis.exceptions.DataError(
            "Invalid data format for Redis"
        )

        with patch.object(api_service.client, "get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": [{"id": "model-1"}]}
            mock_get.return_value = mock_response

            # Should complete validation despite cache data error
            result = await api_service.validate_api_key(
                ServiceType.OPENAI, "sk-test-key-12345", user_id
            )

            assert result.is_valid is True
            assert result.status == ValidationStatus.VALID

    # Comprehensive Failure Scenarios

    @pytest.mark.asyncio
    async def test_cache_failures_during_concurrent_operations(
        self, api_service, mock_dependencies
    ):
        """Test cache failures during concurrent validation operations."""
        user_id = str(uuid.uuid4())

        # Mix of cache failures
        mock_dependencies["cache"].get.side_effect = [
            redis.exceptions.ConnectionError("Connection failed"),
            redis.exceptions.TimeoutError("Timeout"),
            None,  # Success case
        ]
        mock_dependencies["cache"].set.side_effect = redis.exceptions.ConnectionError(
            "Write failed"
        )

        with patch.object(api_service.client, "get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": [{"id": "model-1"}]}
            mock_get.return_value = mock_response

            # Run concurrent validations
            tasks = [
                api_service.validate_api_key(ServiceType.OPENAI, f"sk-key-{i}", user_id)
                for i in range(3)
            ]
            results = await asyncio.gather(*tasks)

            # All should succeed despite cache failures
            for result in results:
                assert result.is_valid is True
                assert result.status == ValidationStatus.VALID

    @pytest.mark.asyncio
    async def test_cache_failure_logging_behavior(
        self, api_service, mock_dependencies, caplog
    ):
        """Test that cache failures are properly logged as warnings."""
        user_id = str(uuid.uuid4())

        # Set up cache to fail with connection error
        mock_dependencies["cache"].get.side_effect = redis.exceptions.ConnectionError(
            "Cache connection lost"
        )

        with patch.object(api_service.client, "get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": [{"id": "model-1"}]}
            mock_get.return_value = mock_response

            # Perform validation
            result = await api_service.validate_api_key(
                ServiceType.OPENAI, "sk-test-key-12345", user_id
            )

            assert result.is_valid is True

            # Check that warning was logged
            warning_logs = [
                record for record in caplog.records if record.levelname == "WARNING"
            ]
            assert len(warning_logs) >= 1
            assert "Cache retrieval error" in warning_logs[0].message

    @pytest.mark.asyncio
    async def test_cache_successful_retrieval_after_failures(
        self, api_service, mock_dependencies
    ):
        """Test that cache works normally after previous failures."""
        user_id = str(uuid.uuid4())

        # First call fails, second succeeds with cached data
        cached_result = {
            "is_valid": True,
            "status": "valid",
            "service": "openai",
            "latency_ms": 50.0,
            "message": "Cached validation result",
        }

        mock_dependencies["cache"].get.side_effect = [
            redis.exceptions.ConnectionError("Connection failed"),
            json.dumps(cached_result),  # Second call returns cached data
        ]

        with patch.object(api_service.client, "get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": [{"id": "model-1"}]}
            mock_get.return_value = mock_response

            # First validation - cache fails, real validation occurs
            result1 = await api_service.validate_api_key(
                ServiceType.OPENAI, "sk-test-key-12345", user_id
            )
            assert result1.is_valid is True
            assert mock_get.call_count == 1

            # Second validation - should use cached result
            result2 = await api_service.validate_api_key(
                ServiceType.OPENAI, "sk-test-key-12345", user_id
            )
            assert result2.is_valid is True
            assert result2.message == "Cached validation result"
            # No additional API calls should be made
            assert mock_get.call_count == 1

    @pytest.mark.asyncio
    async def test_cache_key_generation_with_special_characters(
        self, api_service, mock_dependencies
    ):
        """Test cache key generation handles special characters in keys."""
        user_id = str(uuid.uuid4())

        # Test with key containing special characters
        special_key = "sk-test:key/with#special@chars"

        mock_dependencies["cache"].get.return_value = None
        mock_dependencies["cache"].set.return_value = True

        with patch.object(api_service.client, "get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": [{"id": "model-1"}]}
            mock_get.return_value = mock_response

            # Should handle special characters in cache key generation
            result = await api_service.validate_api_key(
                ServiceType.OPENAI, special_key, user_id
            )

            assert result.is_valid is True
            # Verify cache operations were attempted
            mock_dependencies["cache"].get.assert_called_once()
            mock_dependencies["cache"].set.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_ttl_configuration_resilience(
        self, api_service, mock_dependencies
    ):
        """Test cache operations work with different TTL configurations."""
        user_id = str(uuid.uuid4())

        mock_dependencies["cache"].get.return_value = None
        mock_dependencies["cache"].set.return_value = True

        with patch.object(api_service.client, "get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": [{"id": "model-1"}]}
            mock_get.return_value = mock_response

            # Perform validation
            result = await api_service.validate_api_key(
                ServiceType.OPENAI, "sk-test-key-12345", user_id
            )

            assert result.is_valid is True

            # Verify cache.set was called with proper TTL (300 seconds = 5 minutes)
            call_args = mock_dependencies["cache"].set.call_args
            assert call_args is not None
            assert call_args[1]["ex"] == 300  # TTL should be 5 minutes

    # Targeted Test for Lines 1128-1159 Specific Patterns

    @pytest.mark.asyncio
    async def test_cache_methods_direct_coverage(self, api_service, mock_dependencies):
        """Direct test of cache methods to ensure lines 1128-1159 are covered."""
        service_type = ServiceType.OPENAI
        key_value = "sk-test-key-12345"

        # Test _get_cached_validation with various failure modes

        # 1. Test with no cache service (lines 1135-1136)
        service_no_cache = ApiKeyService(db=mock_dependencies["db"], cache=None)
        result = await service_no_cache._get_cached_validation(service_type, key_value)
        assert result is None

        # 2. Test with cache get exception (lines 1150-1151)
        mock_dependencies["cache"].get.side_effect = Exception("Cache error")
        result = await api_service._get_cached_validation(service_type, key_value)
        assert result is None

        # 3. Test with corrupted JSON data (lines 1147-1148)
        mock_dependencies["cache"].get.side_effect = None
        mock_dependencies["cache"].get.return_value = "{invalid json"
        result = await api_service._get_cached_validation(service_type, key_value)
        assert result is None

        # 4. Test with valid JSON but invalid ValidationResult data
        mock_dependencies["cache"].get.return_value = json.dumps({"invalid": "data"})
        result = await api_service._get_cached_validation(service_type, key_value)
        assert result is None

        # Test _cache_validation_result with various failure modes

        validation_result = ValidationResult(
            is_valid=True,
            status=ValidationStatus.VALID,
            service=service_type,
            message="Test result",
        )

        # 5. Test with no cache service (lines 1159-1160)
        await service_no_cache._cache_validation_result(
            service_type, key_value, validation_result
        )
        # Should complete without error

        # 6. Test with cache set exception (lines 1175-1176)
        mock_dependencies["cache"].set.side_effect = Exception("Cache write error")
        await api_service._cache_validation_result(
            service_type, key_value, validation_result
        )
        # Should complete without error (exception is caught and logged)

        # 7. Test successful path for coverage
        mock_dependencies["cache"].set.side_effect = None
        mock_dependencies["cache"].set.return_value = True
        await api_service._cache_validation_result(
            service_type, key_value, validation_result
        )
        mock_dependencies["cache"].set.assert_called()

    @pytest.mark.asyncio
    async def test_cache_key_generation_security(self, api_service):
        """Test that cache keys are securely generated with SHA256 hashing."""
        service_type = ServiceType.OPENAI
        key_value = "sk-test-sensitive-key"

        # Mock cache to capture the cache key used
        cache_calls = []

        async def mock_cache_get(key):
            cache_calls.append(key)
            return None

        with patch.object(api_service.cache, "get", side_effect=mock_cache_get):
            await api_service._get_cached_validation(service_type, key_value)

        # Verify cache key format and security
        assert len(cache_calls) == 1
        cache_key = cache_calls[0]

        # Should use the v2 format with SHA256 hash
        assert cache_key.startswith("api_validation:v2:")
        assert (
            len(cache_key) == len("api_validation:v2:") + 64
        )  # SHA256 hash is 64 chars

        # Key should not contain the actual API key value
        assert key_value not in cache_key
        assert "sensitive" not in cache_key
