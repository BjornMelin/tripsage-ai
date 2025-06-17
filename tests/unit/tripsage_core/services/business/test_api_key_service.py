"""
Comprehensive tests for ApiKeyService.

This module provides full test coverage for the modern API key service
including validation, storage, rotation, and monitoring functionality.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from tripsage_core.exceptions import (
    CoreServiceError as ServiceError,
)
from tripsage_core.exceptions import (
    CoreValidationError as ValidationError,
)
from tripsage_core.services.business.api_key_service import (
    ApiKeyCreateRequest,
    ApiKeyResponse,
    ApiKeyService,
    ServiceType,
    ValidationResult,
    ValidationStatus,
    get_api_key_service,
)


class TestApiKeyService:
    """Test suite for ApiKeyService."""

    @pytest.fixture
    def mock_db_service(self):
        """Mock database service."""
        db = AsyncMock()
        return db

    @pytest.fixture
    def mock_cache_service(self):
        """Mock cache service."""
        cache = AsyncMock()
        return cache

    @pytest.fixture
    def mock_audit_service(self):
        """Mock audit service."""
        audit = AsyncMock()
        return audit

    @pytest.fixture
    def api_key_service(self, mock_db_service, mock_cache_service, mock_audit_service):
        """Create ApiKeyService instance with mocked dependencies."""
        service = ApiKeyService()
        service.db = mock_db_service
        service.cache = mock_cache_service
        service.audit = mock_audit_service
        return service

    @pytest.fixture
    def sample_create_request(self):
        """Sample API key creation request."""
        return ApiKeyCreateRequest(
            name="OpenAI API Key",
            service=ServiceType.OPENAI,
            key_value="sk-test_key_for_unit_tests",
            description="Key for GPT-4 access",
        )

    @pytest.fixture
    def sample_key_response(self):
        """Sample API key response."""
        return ApiKeyResponse(
            id=str(uuid4()),
            name="OpenAI API Key",
            service=ServiceType.OPENAI,
            description="Key for GPT-4 access",
            is_valid=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=365),
            last_used=None,
            last_validated=datetime.now(timezone.utc),
            usage_count=0,
        )

    @pytest.fixture
    def sample_db_result(self):
        """Sample database result."""
        return {
            "id": str(uuid4()),
            "name": "OpenAI API Key",
            "service": "openai",
            "description": "Key for GPT-4 access",
            "is_valid": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (
                datetime.now(timezone.utc) + timedelta(days=365)
            ).isoformat(),
            "last_used": None,
            "last_validated": datetime.now(timezone.utc).isoformat(),
            "usage_count": 0,
        }

    @pytest.mark.asyncio
    async def test_create_key_success(
        self, api_key_service, mock_db_service, sample_create_request, sample_db_result
    ):
        """Test successful API key creation."""
        user_id = str(uuid4())

        # Mock successful validation
        with patch.object(api_key_service, "validate_api_key") as mock_validate:
            mock_validate.return_value = ValidationResult(
                is_valid=True,
                status=ValidationStatus.VALID,
                service=ServiceType.OPENAI,
                message="Key is valid",
            )

            # Mock database operations
            mock_db_service.create_api_key.return_value = sample_db_result

            result = await api_key_service.create_key(user_id, sample_create_request)

            # Assertions
            assert result.name == sample_create_request.name
            assert result.service == sample_create_request.service
            assert result.description == sample_create_request.description
            assert result.is_valid is True

            # Verify service calls
            mock_validate.assert_called_once()
            mock_db_service.create_api_key.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_key_validation_failed(
        self, api_key_service, sample_create_request
    ):
        """Test API key creation with validation failure."""
        user_id = str(uuid4())

        # Mock validation failure
        with patch.object(api_key_service, "validate_api_key") as mock_validate:
            mock_validate.return_value = ValidationResult(
                is_valid=False,
                status=ValidationStatus.INVALID,
                service=ServiceType.OPENAI,
                message="Invalid API key format",
            )

            with pytest.raises(ValidationError, match="API key validation failed"):
                await api_key_service.create_api_key(user_id, sample_create_request)

    @pytest.mark.asyncio
    async def test_validate_key_openai_success(self, api_key_service):
        """Test successful OpenAI API key validation."""
        with patch("httpx.AsyncClient.get") as mock_get:
            # Mock successful OpenAI response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": [{"id": "model-1"}]}
            mock_get.return_value = mock_response

            result = await api_key_service.validate_api_key(
                ServiceType.OPENAI, "sk-test_key", str(uuid4())
            )

            assert result.is_valid is True
            assert result.status == ValidationStatus.VALID
            assert "OpenAI key is valid" in result.message

    @pytest.mark.asyncio
    async def test_validate_key_openai_invalid(self, api_key_service):
        """Test invalid OpenAI API key validation."""
        with patch("httpx.AsyncClient.get") as mock_get:
            # Mock invalid key response
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.json.return_value = {"error": {"message": "Invalid API key"}}
            mock_get.return_value = mock_response

            result = await api_key_service.validate_key(
                "sk-invalid_key", ServiceType.OPENAI, str(uuid4())
            )

            assert result.is_valid is False
            assert result.status == ValidationStatus.INVALID

    @pytest.mark.asyncio
    async def test_validate_key_format_error(self, api_key_service):
        """Test API key validation with format error."""
        result = await api_key_service.validate_key(
            "invalid_format", ServiceType.OPENAI, str(uuid4())
        )

        assert result.is_valid is False
        assert result.status == ValidationStatus.FORMAT_ERROR

    @pytest.mark.asyncio
    async def test_validate_key_rate_limited(self, api_key_service):
        """Test API key validation when rate limited."""
        with patch("httpx.AsyncClient.get") as mock_get:
            # Mock rate limit response
            mock_response = Mock()
            mock_response.status_code = 429
            mock_get.return_value = mock_response

            result = await api_key_service.validate_key(
                "sk-test_key", ServiceType.OPENAI, str(uuid4())
            )

            assert result.is_valid is False
            assert result.status == ValidationStatus.RATE_LIMITED

    @pytest.mark.asyncio
    async def test_validate_key_with_retry(self, api_key_service):
        """Test API key validation with retry mechanism."""
        with patch("httpx.AsyncClient.get") as mock_get:
            # First call fails, second succeeds
            mock_response_fail = Mock()
            mock_response_fail.status_code = 500

            mock_response_success = Mock()
            mock_response_success.status_code = 200
            mock_response_success.json.return_value = {"data": [{"id": "model-1"}]}

            mock_get.side_effect = [mock_response_fail, mock_response_success]

            result = await api_key_service.validate_key(
                "sk-test_key", ServiceType.OPENAI, str(uuid4())
            )

            assert result.is_valid is True
            assert mock_get.call_count == 2

    @pytest.mark.asyncio
    async def test_get_key_success(
        self, api_key_service, mock_db_service, sample_db_result
    ):
        """Test successful API key retrieval."""
        key_id = str(uuid4())
        mock_db_service.get_api_key.return_value = sample_db_result

        result = await api_key_service.get_key(key_id)

        assert result is not None
        assert result["id"] == sample_db_result["id"]
        assert result["name"] == sample_db_result["name"]
        mock_db_service.get_api_key.assert_called_once_with(key_id)

    @pytest.mark.asyncio
    async def test_get_key_not_found(self, api_key_service, mock_db_service):
        """Test API key retrieval when key doesn't exist."""
        key_id = str(uuid4())
        mock_db_service.get_api_key.return_value = None

        result = await api_key_service.get_key(key_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_list_user_keys_success(
        self, api_key_service, mock_db_service, sample_db_result
    ):
        """Test successful user keys listing."""
        user_id = str(uuid4())
        mock_db_service.list_user_keys.return_value = [sample_db_result]

        results = await api_key_service.list_user_keys(user_id)

        assert len(results) == 1
        assert results[0].id == sample_db_result["id"]
        mock_db_service.list_user_keys.assert_called_once_with(user_id)

    @pytest.mark.asyncio
    async def test_delete_key_success(self, api_key_service, mock_db_service):
        """Test successful API key deletion."""
        key_id = str(uuid4())
        mock_db_service.delete_api_key.return_value = True

        result = await api_key_service.delete_key(key_id)

        assert result is True
        mock_db_service.delete_api_key.assert_called_once_with(key_id)

    @pytest.mark.asyncio
    async def test_rotate_key_success(
        self, api_key_service, mock_db_service, sample_db_result
    ):
        """Test successful API key rotation."""
        key_id = str(uuid4())
        new_key = "sk-new_test_key"
        user_id = str(uuid4())

        # Mock validation success
        with patch.object(api_key_service, "validate_key") as mock_validate:
            mock_validate.return_value = ValidationResult(
                is_valid=True,
                status=ValidationStatus.VALID,
                service=ServiceType.OPENAI,
                message="Key is valid"
            )

            # Mock database operations
            mock_db_service.update_api_key.return_value = sample_db_result

            result = await api_key_service.rotate_key(key_id, new_key, user_id)

            assert result.id == sample_db_result["id"]
            mock_validate.assert_called_once()
            mock_db_service.update_api_key.assert_called_once()

    @pytest.mark.asyncio
    async def test_rotate_key_validation_failed(self, api_key_service):
        """Test API key rotation with validation failure."""
        key_id = str(uuid4())
        new_key = "invalid_key"
        user_id = str(uuid4())

        # Mock validation failure
        with patch.object(api_key_service, "validate_key") as mock_validate:
            mock_validate.return_value = ValidationResult(
                is_valid=False,
                status=ValidationStatus.INVALID,
                service=ServiceType.OPENAI,
                message="Invalid key format",
            )

            with pytest.raises(ValidationError, match="New API key validation failed"):
                await api_key_service.rotate_key(key_id, new_key, user_id)

    @pytest.mark.asyncio
    async def test_check_health_success(self, api_key_service, mock_db_service):
        """Test successful health check."""
        key_id = str(uuid4())

        # Mock successful health check
        with patch.object(api_key_service, "validate_key") as mock_validate:
            mock_validate.return_value = ValidationResult(
                is_valid=True,
                status=ValidationStatus.VALID,
                service=ServiceType.OPENAI,
                message="Key is healthy"
            )

            mock_db_service.get_api_key.return_value = {
                "id": key_id,
                "service": "openai",
                "encrypted_key": "encrypted_value",
            }

            with patch.object(api_key_service, "_decrypt_key") as mock_decrypt:
                mock_decrypt.return_value = "sk-test_key"

                result = await api_key_service.check_health(key_id)

                assert result.is_valid is True
                assert result.status == ValidationStatus.VALID

    @pytest.mark.asyncio
    async def test_check_health_key_not_found(self, api_key_service, mock_db_service):
        """Test health check when key doesn't exist."""
        key_id = str(uuid4())
        mock_db_service.get_api_key.return_value = None

        with pytest.raises(ValidationError, match="API key not found"):
            await api_key_service.check_health(key_id)

    @pytest.mark.asyncio
    async def test_monitor_key_success(
        self, api_key_service, mock_db_service, mock_cache_service
    ):
        """Test successful key monitoring."""
        key_id = str(uuid4())
        user_id = str(uuid4())

        # Mock monitoring data
        mock_cache_service.get_json.return_value = {
            "last_check": datetime.now(timezone.utc).isoformat(),
            "status": "healthy",
            "response_time": 150,
        }

        result = await api_key_service.monitor_key(key_id, user_id)

        assert "last_check" in result
        assert result["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_encrypt_decrypt_key(self, api_key_service):
        """Test key encryption and decryption."""
        test_key = "sk-test_key_for_encryption"

        # Test encryption
        encrypted = api_key_service._encrypt_key(test_key)
        assert encrypted != test_key
        assert len(encrypted) > len(test_key)

        # Test decryption
        decrypted = api_key_service._decrypt_key(encrypted)
        assert decrypted == test_key

    @pytest.mark.asyncio
    async def test_cache_operations(self, api_key_service, mock_cache_service):
        """Test cache operations for validation results."""
        key_hash = "test_hash"
        validation_result = ValidationResult(
            is_valid=True,
            status=ValidationStatus.VALID,
            service=ServiceType.OPENAI,
            message="Cached result"
        )

        # Test cache set
        await api_key_service._cache_validation_result(key_hash, validation_result)
        mock_cache_service.set_json.assert_called_once()

        # Test cache get
        mock_cache_service.get_json.return_value = {
            "is_valid": True,
            "status": "valid",
            "message": "Cached result",
            "expires_at": (
                datetime.now(timezone.utc) + timedelta(minutes=5)
            ).isoformat(),
        }

        result = await api_key_service._get_cached_validation(key_hash)
        assert result is not None
        assert result.is_valid is True

    @pytest.mark.asyncio
    async def test_rate_limiting(self, api_key_service, mock_cache_service):
        """Test rate limiting functionality."""
        user_id = str(uuid4())

        # Mock no previous requests
        mock_cache_service.get.return_value = None

        is_limited = await api_key_service._is_rate_limited(user_id)
        assert is_limited is False

        # Mock rate limit exceeded
        mock_cache_service.get.return_value = "10"  # 10 requests in current window

        is_limited = await api_key_service._is_rate_limited(user_id)
        assert is_limited is True

    @pytest.mark.asyncio
    async def test_usage_logging(self, api_key_service, mock_db_service):
        """Test usage logging functionality."""
        key_id = str(uuid4())
        user_id = str(uuid4())

        await api_key_service._log_usage(
            key_id=key_id,
            user_id=user_id,
            service="openai",
            operation="validation",
            success=True,
        )

        mock_db_service.log_api_key_usage.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_handling_database_failure(
        self, api_key_service, mock_db_service, sample_create_request
    ):
        """Test error handling when database operations fail."""
        user_id = str(uuid4())

        # Mock validation success but database failure
        with patch.object(api_key_service, "validate_key") as mock_validate:
            mock_validate.return_value = ValidationResult(
                is_valid=True,
                status=ValidationStatus.VALID,
                service=ServiceType.OPENAI,
                message="Key is valid"
            )

            mock_db_service.create_api_key.side_effect = Exception("Database error")

            with pytest.raises(ServiceError, match="Failed to create API key"):
                await api_key_service.create_key(user_id, sample_create_request)

    @pytest.mark.asyncio
    async def test_error_handling_network_failure(self, api_key_service):
        """Test error handling when network requests fail."""
        with patch("httpx.AsyncClient.get") as mock_get:
            # Mock network failure
            mock_get.side_effect = Exception("Network error")

            result = await api_key_service.validate_key(
                "sk-test_key", ServiceType.OPENAI, str(uuid4())
            )

            assert result.is_valid is False
            assert result.status == ValidationStatus.SERVICE_ERROR

    @pytest.mark.asyncio
    async def test_service_specific_validation_weather(self, api_key_service):
        """Test weather service specific validation."""
        with patch("httpx.AsyncClient.get") as mock_get:
            # Mock successful weather API response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"current": {"temp_c": 20}}
            mock_get.return_value = mock_response

            result = await api_key_service.validate_key(
                "test_weather_key", ServiceType.WEATHER, str(uuid4())
            )

            assert result.is_valid is True
            assert result.status == ValidationStatus.VALID

    @pytest.mark.asyncio
    async def test_service_specific_validation_google_maps(self, api_key_service):
        """Test Google Maps service specific validation."""
        with patch("httpx.AsyncClient.get") as mock_get:
            # Mock successful Google Maps API response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "OK", "results": []}
            mock_get.return_value = mock_response

            result = await api_key_service.validate_key(
                "test_google_key", ServiceType.GOOGLEMAPS, str(uuid4())
            )

            assert result.is_valid is True
            assert result.status == ValidationStatus.VALID

    @pytest.mark.asyncio
    async def test_bulk_operations(
        self, api_key_service, mock_db_service, sample_db_result
    ):
        """Test bulk key operations."""
        user_id = str(uuid4())

        # Mock database response
        mock_db_service.list_user_keys.return_value = [sample_db_result] * 3

        # Test bulk health check
        with patch.object(api_key_service, "check_health") as mock_health:
            mock_health.return_value = ValidationResult(
                is_valid=True,
                status=ValidationStatus.VALID,
                service=ServiceType.OPENAI,
                message="Healthy"
            )

            results = await api_key_service.bulk_health_check(user_id)

            assert len(results) == 3
            assert all(result["status"] == "healthy" for result in results)

    def test_get_api_key_service_dependency(self):
        """Test the dependency injection function."""
        service = get_api_key_service()
        assert isinstance(service, ApiKeyService)

    @pytest.mark.asyncio
    async def test_service_initialization(self, api_key_service):
        """Test service initialization."""
        await api_key_service.initialize()

        # Verify dependencies are initialized
        assert api_key_service.db is not None
        assert api_key_service.cache is not None
        assert api_key_service.audit is not None

    @pytest.mark.asyncio
    async def test_validation_caching_behavior(
        self, api_key_service, mock_cache_service
    ):
        """Test that validation results are properly cached."""
        # Mock cache miss
        mock_cache_service.get_json.return_value = None

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": [{"id": "model-1"}]}
            mock_get.return_value = mock_response

            # First validation should hit the API
            result1 = await api_key_service.validate_key(
                "sk-test_key", ServiceType.OPENAI, str(uuid4())
            )

            # Verify cache was called to store result
            mock_cache_service.set_json.assert_called()

            # Mock cache hit for second call
            mock_cache_service.get_json.return_value = {
                "is_valid": True,
                "status": "valid",
                "message": "Cached result",
                "expires_at": (
                    datetime.now(timezone.utc) + timedelta(minutes=5)
                ).isoformat(),
            }

            # Second validation should use cache
            result2 = await api_key_service.validate_key(
                "sk-test_key", ServiceType.OPENAI, str(uuid4())
            )

            assert result1.is_valid is True
            assert result2.is_valid is True
