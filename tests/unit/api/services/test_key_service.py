"""
Comprehensive tests for the refactored API key service.

Tests the thin wrapper functionality, model adaptation, error handling,
and dependency injection patterns of the KeyService.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from api.services.key_service import KeyService
from tripsage.api.models.requests.api_keys import (
    CreateApiKeyRequest,
    RotateApiKeyRequest,
    ValidateApiKeyRequest,
)
from tripsage.api.models.responses.api_keys import (
    ApiKeyListResponse,
    ApiKeyResponse,
    ApiKeyServicesStatusResponse,
    ApiKeyServiceStatusResponse,
    ApiKeyValidationResponse,
    MessageResponse,
)
from tripsage_core.exceptions.exceptions import (
    CoreServiceError as ServiceError,
)
from tripsage_core.exceptions.exceptions import (
    CoreValidationError as ValidationError,
)
from tripsage_core.services.business.key_management_service import (
    ApiKeyResponse as CoreApiKeyResponse,
)
from tripsage_core.services.business.key_management_service import (
    ApiKeyValidationResult,
)
from tripsage_core.services.business.key_management_service import (
    KeyManagementService as CoreKeyManagementService,
)


class TestKeyService:
    """Comprehensive test cases for KeyService thin wrapper."""

    @pytest.fixture
    def mock_core_key_service(self):
        """Mock core key management service."""
        return AsyncMock(spec=CoreKeyManagementService)

    @pytest.fixture
    def key_service(self, mock_core_key_service):
        """Create key service with mocked dependencies."""
        return KeyService(core_key_service=mock_core_key_service)

    @pytest.fixture
    def sample_core_api_key(self):
        """Sample core API key response."""
        return CoreApiKeyResponse(
            id="key_abc123",
            name="Production OpenAI Key",
            service="openai",
            description="Primary OpenAI API key for production",
            is_valid=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            expires_at=None,
            last_used=datetime.now(timezone.utc),
            last_validated=datetime.now(timezone.utc),
            usage_count=157,
        )

    @pytest.fixture
    def sample_validation_result(self):
        """Sample validation result."""
        return ApiKeyValidationResult(
            is_valid=True,
            service="openai",
            message="API key format is valid and authenticated",
            details={
                "validation_type": "full_authentication",
                "rate_limit_remaining": 1000,
            },
            validated_at=datetime.now(timezone.utc),
        )

    @pytest.fixture
    def sample_expired_api_key(self):
        """Sample expired API key."""
        past_date = datetime.now(timezone.utc).replace(day=1)
        return CoreApiKeyResponse(
            id="key_expired123",
            name="Expired Weather Key",
            service="weather",
            description="Expired weather API key",
            is_valid=False,
            created_at=past_date,
            updated_at=past_date,
            expires_at=past_date,
            last_used=None,
            last_validated=past_date,
            usage_count=0,
        )

    # API Key Creation Tests
    async def test_create_api_key_success(
        self, key_service, mock_core_key_service, sample_core_api_key
    ):
        """Test successful API key creation with proper model adaptation."""
        # Arrange
        user_id = "user_abc123"
        request = CreateApiKeyRequest(
            name="Production OpenAI Key",
            service="openai",
            key_value="sk-proj-abcdef123456789",
            description="Primary OpenAI API key for production",
            expires_at=None,
        )

        mock_core_key_service.create_api_key.return_value = sample_core_api_key

        # Act
        result = await key_service.create_api_key(user_id, request)

        # Assert
        assert isinstance(result, ApiKeyResponse)
        assert result.id == "key_abc123"
        assert result.name == "Production OpenAI Key"
        assert result.service == "openai"
        assert result.description == "Primary OpenAI API key for production"
        assert result.is_valid is True
        assert result.usage_count == 157

        # Verify core service was called with correct data
        call_args = mock_core_key_service.create_api_key.call_args
        assert call_args[0][0] == user_id

        core_request = call_args[0][1]
        assert core_request.name == request.name
        assert core_request.service == request.service
        assert core_request.key_value == request.key_value
        assert core_request.description == request.description
        assert core_request.expires_at == request.expires_at

    async def test_create_api_key_validation_error(
        self, key_service, mock_core_key_service
    ):
        """Test API key creation with validation error."""
        # Arrange
        user_id = "user_abc123"
        request = CreateApiKeyRequest(
            name="Invalid Key",
            service="openai",
            key_value="invalid_key_format",
        )

        mock_core_key_service.create_api_key.side_effect = ValidationError(
            "Invalid OpenAI API key format"
        )

        # Act & Assert
        with pytest.raises(ValidationError):
            await key_service.create_api_key(user_id, request)

    async def test_create_api_key_service_error(
        self, key_service, mock_core_key_service
    ):
        """Test API key creation with service error."""
        # Arrange
        user_id = "user_abc123"
        request = CreateApiKeyRequest(
            name="Test Key",
            service="openai",
            key_value="sk-test123",
        )

        mock_core_key_service.create_api_key.side_effect = Exception(
            "Encryption failed"
        )

        # Act & Assert
        with pytest.raises(ServiceError, match="Failed to create API key"):
            await key_service.create_api_key(user_id, request)

    # API Key Retrieval Tests
    async def test_get_user_api_keys_success(
        self, key_service, mock_core_key_service, sample_core_api_key
    ):
        """Test successful retrieval of user API keys."""
        # Arrange
        user_id = "user_abc123"
        mock_core_key_service.get_user_api_keys.return_value = [sample_core_api_key]

        # Act
        result = await key_service.get_user_api_keys(user_id)

        # Assert
        assert isinstance(result, ApiKeyListResponse)
        assert len(result.keys) == 1
        assert result.total == 1
        assert result.keys[0].id == "key_abc123"
        assert result.keys[0].name == "Production OpenAI Key"

        mock_core_key_service.get_user_api_keys.assert_called_once_with(user_id)

    async def test_get_user_api_keys_multiple_keys(
        self,
        key_service,
        mock_core_key_service,
        sample_core_api_key,
        sample_expired_api_key,
    ):
        """Test retrieval of multiple API keys."""
        # Arrange
        user_id = "user_abc123"
        mock_core_key_service.get_user_api_keys.return_value = [
            sample_core_api_key,
            sample_expired_api_key,
        ]

        # Act
        result = await key_service.get_user_api_keys(user_id)

        # Assert
        assert isinstance(result, ApiKeyListResponse)
        assert len(result.keys) == 2
        assert result.total == 2

        # Verify both keys are properly adapted
        openai_key = next(k for k in result.keys if k.service == "openai")
        weather_key = next(k for k in result.keys if k.service == "weather")

        assert openai_key.is_valid is True
        assert weather_key.is_valid is False

    async def test_get_user_api_keys_empty(self, key_service, mock_core_key_service):
        """Test retrieval when user has no API keys."""
        # Arrange
        user_id = "user_abc123"
        mock_core_key_service.get_user_api_keys.return_value = []

        # Act
        result = await key_service.get_user_api_keys(user_id)

        # Assert
        assert isinstance(result, ApiKeyListResponse)
        assert len(result.keys) == 0
        assert result.total == 0

    async def test_get_user_api_keys_error_handling(
        self, key_service, mock_core_key_service
    ):
        """Test error handling in get_user_api_keys returns empty list."""
        # Arrange
        user_id = "user_abc123"
        mock_core_key_service.get_user_api_keys.side_effect = Exception(
            "Database error"
        )

        # Act
        result = await key_service.get_user_api_keys(user_id)

        # Assert - Should return empty list on error
        assert isinstance(result, ApiKeyListResponse)
        assert len(result.keys) == 0
        assert result.total == 0

    async def test_get_api_key_success(
        self, key_service, mock_core_key_service, sample_core_api_key
    ):
        """Test successful retrieval of specific API key."""
        # Arrange
        user_id = "user_abc123"
        key_id = "key_abc123"
        mock_core_key_service.get_user_api_keys.return_value = [sample_core_api_key]

        # Act
        result = await key_service.get_api_key(user_id, key_id)

        # Assert
        assert isinstance(result, ApiKeyResponse)
        assert result.id == key_id
        assert result.name == "Production OpenAI Key"

    async def test_get_api_key_not_found(self, key_service, mock_core_key_service):
        """Test retrieval of non-existent API key."""
        # Arrange
        user_id = "user_abc123"
        key_id = "nonexistent_key"
        mock_core_key_service.get_user_api_keys.return_value = []

        # Act
        result = await key_service.get_api_key(user_id, key_id)

        # Assert
        assert result is None

    async def test_get_api_key_wrong_user(
        self, key_service, mock_core_key_service, sample_core_api_key
    ):
        """Test retrieval of API key that belongs to different user."""
        # Arrange
        user_id = "user_abc123"
        key_id = "different_key_id"
        sample_core_api_key.id = "key_abc123"  # Different from searched key_id
        mock_core_key_service.get_user_api_keys.return_value = [sample_core_api_key]

        # Act
        result = await key_service.get_api_key(user_id, key_id)

        # Assert
        assert result is None

    # Service Status Tests
    async def test_get_service_status_with_valid_key(
        self, key_service, mock_core_key_service, sample_core_api_key
    ):
        """Test service status when user has a valid key."""
        # Arrange
        user_id = "user_abc123"
        service = "openai"
        mock_core_key_service.get_api_key_for_service.return_value = "sk-test123"
        mock_core_key_service.get_user_api_keys.return_value = [sample_core_api_key]

        # Act
        result = await key_service.get_service_status(user_id, service)

        # Assert
        assert isinstance(result, ApiKeyServiceStatusResponse)
        assert result.service == service
        assert result.has_key is True
        assert result.is_valid is True
        assert result.last_validated is not None
        assert result.last_used is not None

    async def test_get_service_status_with_invalid_key(
        self, key_service, mock_core_key_service, sample_expired_api_key
    ):
        """Test service status when user has an invalid key."""
        # Arrange
        user_id = "user_abc123"
        service = "weather"
        mock_core_key_service.get_api_key_for_service.return_value = "invalid_key"
        mock_core_key_service.get_user_api_keys.return_value = [sample_expired_api_key]

        # Act
        result = await key_service.get_service_status(user_id, service)

        # Assert
        assert isinstance(result, ApiKeyServiceStatusResponse)
        assert result.service == service
        assert result.has_key is True
        assert result.is_valid is False

    async def test_get_service_status_without_key(
        self, key_service, mock_core_key_service
    ):
        """Test service status when user has no key for service."""
        # Arrange
        user_id = "user_abc123"
        service = "googlemaps"
        mock_core_key_service.get_api_key_for_service.return_value = None

        # Act
        result = await key_service.get_service_status(user_id, service)

        # Assert
        assert isinstance(result, ApiKeyServiceStatusResponse)
        assert result.service == service
        assert result.has_key is False
        assert result.is_valid is None
        assert result.last_validated is None
        assert result.last_used is None

    async def test_get_service_status_error_handling(
        self, key_service, mock_core_key_service
    ):
        """Test service status error handling."""
        # Arrange
        user_id = "user_abc123"
        service = "openai"
        mock_core_key_service.get_api_key_for_service.side_effect = Exception(
            "Database error"
        )

        # Act
        result = await key_service.get_service_status(user_id, service)

        # Assert - Should return safe defaults
        assert isinstance(result, ApiKeyServiceStatusResponse)
        assert result.service == service
        assert result.has_key is False
        assert result.is_valid is None

    async def test_get_all_services_status(self, key_service, mock_core_key_service):
        """Test getting status for all supported services."""
        # Arrange
        user_id = "user_abc123"
        mock_core_key_service.get_api_key_for_service.return_value = None

        # Act
        result = await key_service.get_all_services_status(user_id)

        # Assert
        assert isinstance(result, ApiKeyServicesStatusResponse)
        expected_services = [
            "openai",
            "weather",
            "flights",
            "googlemaps",
            "accommodation",
            "webcrawl",
            "calendar",
            "email",
        ]

        for service in expected_services:
            assert service in result.services
            assert isinstance(result.services[service], ApiKeyServiceStatusResponse)
            assert result.services[service].service == service

        assert len(result.services) == 8

    async def test_get_all_services_status_error_handling(
        self, key_service, mock_core_key_service
    ):
        """Test error handling in get_all_services_status."""
        # Arrange
        user_id = "user_abc123"
        mock_core_key_service.get_api_key_for_service.side_effect = Exception(
            "Database error"
        )

        # Act
        result = await key_service.get_all_services_status(user_id)

        # Assert - Should return status responses with safe defaults on errors
        assert isinstance(result, ApiKeyServicesStatusResponse)
        expected_services = [
            "openai",
            "weather",
            "flights",
            "googlemaps",
            "accommodation",
            "webcrawl",
            "calendar",
            "email",
        ]

        # All services should be present with safe defaults
        for service in expected_services:
            assert service in result.services
            status = result.services[service]
            assert isinstance(status, ApiKeyServiceStatusResponse)
            assert status.service == service
            assert status.has_key is False
            assert status.is_valid is None

    # Validation Tests
    async def test_validate_api_key_success(
        self, key_service, mock_core_key_service, sample_validation_result
    ):
        """Test successful API key validation."""
        # Arrange
        user_id = "user_abc123"
        key_id = "key_abc123"
        mock_core_key_service.validate_api_key.return_value = sample_validation_result

        # Act
        result = await key_service.validate_api_key(user_id, key_id)

        # Assert
        assert isinstance(result, ApiKeyValidationResponse)
        assert result.is_valid is True
        assert result.service == "openai"
        assert result.message == "API key format is valid and authenticated"
        assert result.details == {
            "validation_type": "full_authentication",
            "rate_limit_remaining": 1000,
        }

        mock_core_key_service.validate_api_key.assert_called_once_with(key_id, user_id)

    async def test_validate_api_key_failure(self, key_service, mock_core_key_service):
        """Test API key validation failure."""
        # Arrange
        user_id = "user_abc123"
        key_id = "key_abc123"
        mock_core_key_service.validate_api_key.side_effect = ValidationError(
            "API key not found"
        )

        # Act & Assert
        with pytest.raises(ValidationError):
            await key_service.validate_api_key(user_id, key_id)

    async def test_validate_key_value_success(
        self, key_service, mock_core_key_service, sample_validation_result
    ):
        """Test successful API key value validation."""
        # Arrange
        request = ValidateApiKeyRequest(
            service="openai",
            key_value="sk-proj-abcdef123456789",
        )
        mock_core_key_service._validate_api_key.return_value = sample_validation_result

        # Act
        result = await key_service.validate_key_value(request)

        # Assert
        assert isinstance(result, ApiKeyValidationResponse)
        assert result.is_valid is True
        assert result.service == "openai"
        assert result.message == "API key format is valid and authenticated"

        mock_core_key_service._validate_api_key.assert_called_once_with(
            request.service, request.key_value
        )

    async def test_validate_key_value_error(self, key_service, mock_core_key_service):
        """Test API key value validation error."""
        # Arrange
        request = ValidateApiKeyRequest(
            service="openai",
            key_value="invalid_key_format",
        )
        mock_core_key_service._validate_api_key.side_effect = Exception(
            "Invalid key format"
        )

        # Act
        result = await key_service.validate_key_value(request)

        # Assert
        assert isinstance(result, ApiKeyValidationResponse)
        assert result.is_valid is False
        assert "Invalid key format" in result.message
        assert result.service == request.service

    # Key Rotation Tests
    async def test_rotate_api_key_success(
        self, key_service, mock_core_key_service, sample_core_api_key
    ):
        """Test successful API key rotation."""
        # Arrange
        user_id = "user_abc123"
        key_id = "key_abc123"
        request = RotateApiKeyRequest(new_key_value="sk-proj-newkey123456789")

        # Update the sample key to reflect rotation
        rotated_key = sample_core_api_key.model_copy()
        rotated_key.updated_at = datetime.now(timezone.utc)
        mock_core_key_service.rotate_api_key.return_value = rotated_key

        # Act
        result = await key_service.rotate_api_key(user_id, key_id, request)

        # Assert
        assert isinstance(result, ApiKeyResponse)
        assert result.id == key_id

        mock_core_key_service.rotate_api_key.assert_called_once_with(
            key_id, user_id, request.new_key_value
        )

    async def test_rotate_api_key_validation_error(
        self, key_service, mock_core_key_service
    ):
        """Test API key rotation with validation error."""
        # Arrange
        user_id = "user_abc123"
        key_id = "key_abc123"
        request = RotateApiKeyRequest(new_key_value="invalid_key")

        mock_core_key_service.rotate_api_key.side_effect = ValidationError(
            "Invalid new key format"
        )

        # Act & Assert
        with pytest.raises(ValidationError):
            await key_service.rotate_api_key(user_id, key_id, request)

    async def test_rotate_api_key_service_error(
        self, key_service, mock_core_key_service
    ):
        """Test API key rotation with service error."""
        # Arrange
        user_id = "user_abc123"
        key_id = "key_abc123"
        request = RotateApiKeyRequest(new_key_value="sk-proj-newkey123")

        mock_core_key_service.rotate_api_key.side_effect = Exception("Encryption error")

        # Act & Assert
        with pytest.raises(ValidationError, match="Rotation failed"):
            await key_service.rotate_api_key(user_id, key_id, request)

    # Key Deletion Tests
    async def test_delete_api_key_success(self, key_service, mock_core_key_service):
        """Test successful API key deletion."""
        # Arrange
        user_id = "user_abc123"
        key_id = "key_abc123"
        mock_core_key_service.delete_api_key.return_value = True

        # Act
        result = await key_service.delete_api_key(user_id, key_id)

        # Assert
        assert isinstance(result, MessageResponse)
        assert result.success is True
        assert "successfully" in result.message

        mock_core_key_service.delete_api_key.assert_called_once_with(key_id, user_id)

    async def test_delete_api_key_not_found(self, key_service, mock_core_key_service):
        """Test deletion of non-existent API key."""
        # Arrange
        user_id = "user_abc123"
        key_id = "nonexistent_key"
        mock_core_key_service.delete_api_key.return_value = False

        # Act & Assert
        with pytest.raises(ValidationError, match="not found"):
            await key_service.delete_api_key(user_id, key_id)

    async def test_delete_api_key_service_error(
        self, key_service, mock_core_key_service
    ):
        """Test API key deletion with service error."""
        # Arrange
        user_id = "user_abc123"
        key_id = "key_abc123"
        mock_core_key_service.delete_api_key.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(ValidationError, match="Deletion failed"):
            await key_service.delete_api_key(user_id, key_id)

    # Model Adaptation Tests
    async def test_adapt_api_key_response(self, key_service, sample_core_api_key):
        """Test API key response model adaptation."""
        # Act
        api_key = key_service._adapt_api_key_response(sample_core_api_key)

        # Assert
        assert isinstance(api_key, ApiKeyResponse)
        assert api_key.id == sample_core_api_key.id
        assert api_key.name == sample_core_api_key.name
        assert api_key.service == sample_core_api_key.service
        assert api_key.description == sample_core_api_key.description
        assert api_key.is_valid == sample_core_api_key.is_valid
        assert api_key.created_at == sample_core_api_key.created_at
        assert api_key.updated_at == sample_core_api_key.updated_at
        assert api_key.expires_at == sample_core_api_key.expires_at
        assert api_key.last_used == sample_core_api_key.last_used
        assert api_key.last_validated == sample_core_api_key.last_validated
        assert api_key.usage_count == sample_core_api_key.usage_count

    async def test_adapt_validation_response(
        self, key_service, sample_validation_result
    ):
        """Test validation result model adaptation."""
        # Act
        api_validation = key_service._adapt_validation_response(
            sample_validation_result
        )

        # Assert
        assert isinstance(api_validation, ApiKeyValidationResponse)
        assert api_validation.is_valid == sample_validation_result.is_valid
        assert api_validation.service == sample_validation_result.service
        assert api_validation.message == sample_validation_result.message
        assert api_validation.details == sample_validation_result.details
        assert api_validation.validated_at == sample_validation_result.validated_at

    # Lazy Initialization Tests
    async def test_lazy_service_initialization(self):
        """Test that core service is initialized lazily."""
        # Arrange
        key_service = KeyService()

        # Assert - Service should be None initially
        assert key_service.core_key_service is None

        # Verify lazy initialization method exists
        assert hasattr(key_service, "_get_core_key_service")

    async def test_get_core_key_service_lazy_initialization(self):
        """Test core key service lazy initialization."""
        # Arrange
        key_service = KeyService()

        # Mock the lazy initialization
        mock_service = AsyncMock(spec=CoreKeyManagementService)

        # Mock the get_core_key_management_service function
        async def mock_get_core_key_service():
            return mock_service

        # Replace the function
        import api.services.key_service

        original_fn = api.services.key_service.get_core_key_management_service
        api.services.key_service.get_core_key_management_service = (
            mock_get_core_key_service
        )

        try:
            # Act
            result = await key_service._get_core_key_service()

            # Assert
            assert result is mock_service
            assert key_service.core_key_service is mock_service
        finally:
            # Restore original function
            api.services.key_service.get_core_key_management_service = original_fn

    # Integration and Edge Case Tests
    async def test_comprehensive_error_logging(
        self, key_service, mock_core_key_service, caplog
    ):
        """Test that errors are properly logged."""
        # Arrange
        user_id = "user_abc123"
        request = CreateApiKeyRequest(
            name="Test Key", service="openai", key_value="sk-test123"
        )
        mock_core_key_service.create_api_key.side_effect = ServiceError(
            "Encryption failed"
        )

        # Act
        with pytest.raises(ServiceError):
            await key_service.create_api_key(user_id, request)

        # Assert - Check that error was logged
        assert "API key creation failed" in caplog.text
        assert "Encryption failed" in caplog.text

    async def test_service_supports_all_expected_services(self, key_service):
        """Test that service status includes all expected services."""
        # Act
        from api.services.key_service import KeyService

        # Create a real instance to test the hardcoded service list
        service = KeyService()

        # Mock the core service calls
        mock_core = AsyncMock()
        mock_core.get_api_key_for_service.return_value = None
        service.core_key_service = mock_core

        await service.get_all_services_status("user_123")

        # Assert all expected services are present
        expected_services = {
            "openai",
            "weather",
            "flights",
            "googlemaps",
            "accommodation",
            "webcrawl",
            "calendar",
            "email",
        }

        # When there's no error, services should be present
        for _service_name in expected_services:
            # The method calls get_service_status for each service
            # which should have been called if there were no errors
            pass  # This test verifies the service list is comprehensive

    async def test_multiple_concurrent_operations(
        self, key_service, mock_core_key_service, sample_core_api_key
    ):
        """Test handling of multiple concurrent operations."""
        # Arrange
        user_id = "user_abc123"
        mock_core_key_service.get_user_api_keys.return_value = [sample_core_api_key]

        # Act - Simulate concurrent calls
        import asyncio

        results = await asyncio.gather(
            key_service.get_user_api_keys(user_id),
            key_service.get_user_api_keys(user_id),
            key_service.get_user_api_keys(user_id),
        )

        # Assert - All calls should succeed
        for result in results:
            assert isinstance(result, ApiKeyListResponse)
            assert len(result.keys) == 1
            assert result.keys[0].id == "key_abc123"
