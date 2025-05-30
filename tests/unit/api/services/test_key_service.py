"""
Unit tests for the API key service.

Tests the thin wrapper functionality and model adaptation between
API and core services.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from api.schemas.requests.keys import (
    CreateApiKeyRequest,
    RotateApiKeyRequest,
    ValidateApiKeyRequest,
)
from api.schemas.responses.keys import (
    ApiKeyListResponse,
    ApiKeyResponse,
    ApiKeyServicesStatusResponse,
    ApiKeyServiceStatusResponse,
    ApiKeyValidationResponse,
    MessageResponse,
)
from api.services.key_service import KeyService
from tripsage_core.exceptions.exceptions import (
    CoreServiceError,
    CoreValidationError,
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
    """Test cases for KeyService."""

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
            id="key_123",
            name="Test OpenAI Key",
            service="openai",
            description="Test API key for OpenAI",
            is_valid=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            expires_at=None,
            last_used=datetime.now(timezone.utc),
            last_validated=datetime.now(timezone.utc),
            usage_count=42,
        )

    @pytest.fixture
    def sample_validation_result(self):
        """Sample validation result."""
        return ApiKeyValidationResult(
            is_valid=True,
            service="openai",
            message="API key is valid",
            details={"validation_type": "format_check"},
            validated_at=datetime.now(timezone.utc),
        )

    async def test_create_api_key_success(
        self, key_service, mock_core_key_service, sample_core_api_key
    ):
        """Test successful API key creation."""
        # Arrange
        user_id = "user_123"
        request = CreateApiKeyRequest(
            name="Test OpenAI Key",
            service="openai",
            key_value="sk-test123",
            description="Test API key for OpenAI",
        )

        mock_core_key_service.create_api_key.return_value = sample_core_api_key

        # Act
        result = await key_service.create_api_key(user_id, request)

        # Assert
        assert isinstance(result, ApiKeyResponse)
        assert result.id == "key_123"
        assert result.name == "Test OpenAI Key"
        assert result.service == "openai"
        assert result.is_valid is True

        # Verify core service was called correctly
        mock_core_key_service.create_api_key.assert_called_once()
        call_args = mock_core_key_service.create_api_key.call_args
        assert call_args[0][0] == user_id  # First positional arg
        core_request = call_args[0][1]  # Second positional arg
        assert core_request.name == request.name
        assert core_request.service == request.service
        assert core_request.key_value == request.key_value

    async def test_create_api_key_validation_error(
        self, key_service, mock_core_key_service
    ):
        """Test API key creation with validation error."""
        # Arrange
        user_id = "user_123"
        request = CreateApiKeyRequest(
            name="Test Key",
            service="openai",
            key_value="invalid_key",
        )

        mock_core_key_service.create_api_key.side_effect = CoreValidationError(
            "Invalid API key format"
        )

        # Act & Assert
        with pytest.raises(CoreValidationError):
            await key_service.create_api_key(user_id, request)

    async def test_get_user_api_keys_success(
        self, key_service, mock_core_key_service, sample_core_api_key
    ):
        """Test successful retrieval of user API keys."""
        # Arrange
        user_id = "user_123"
        mock_core_key_service.get_user_api_keys.return_value = [sample_core_api_key]

        # Act
        result = await key_service.get_user_api_keys(user_id)

        # Assert
        assert isinstance(result, ApiKeyListResponse)
        assert len(result.keys) == 1
        assert result.total == 1
        assert result.keys[0].id == "key_123"

        mock_core_key_service.get_user_api_keys.assert_called_once_with(user_id)

    async def test_get_user_api_keys_empty(self, key_service, mock_core_key_service):
        """Test retrieval of user API keys when none exist."""
        # Arrange
        user_id = "user_123"
        mock_core_key_service.get_user_api_keys.return_value = []

        # Act
        result = await key_service.get_user_api_keys(user_id)

        # Assert
        assert isinstance(result, ApiKeyListResponse)
        assert len(result.keys) == 0
        assert result.total == 0

    async def test_get_user_api_keys_error(self, key_service, mock_core_key_service):
        """Test error handling in get_user_api_keys."""
        # Arrange
        user_id = "user_123"
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
        user_id = "user_123"
        key_id = "key_123"
        mock_core_key_service.get_user_api_keys.return_value = [sample_core_api_key]

        # Act
        result = await key_service.get_api_key(user_id, key_id)

        # Assert
        assert isinstance(result, ApiKeyResponse)
        assert result.id == key_id

    async def test_get_api_key_not_found(self, key_service, mock_core_key_service):
        """Test retrieval of non-existent API key."""
        # Arrange
        user_id = "user_123"
        key_id = "nonexistent_key"
        mock_core_key_service.get_user_api_keys.return_value = []

        # Act
        result = await key_service.get_api_key(user_id, key_id)

        # Assert
        assert result is None

    async def test_get_service_status_with_key(
        self, key_service, mock_core_key_service, sample_core_api_key
    ):
        """Test service status when user has a key."""
        # Arrange
        user_id = "user_123"
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

    async def test_get_service_status_without_key(
        self, key_service, mock_core_key_service
    ):
        """Test service status when user has no key."""
        # Arrange
        user_id = "user_123"
        service = "openai"
        mock_core_key_service.get_api_key_for_service.return_value = None

        # Act
        result = await key_service.get_service_status(user_id, service)

        # Assert
        assert isinstance(result, ApiKeyServiceStatusResponse)
        assert result.service == service
        assert result.has_key is False
        assert result.is_valid is None

    async def test_get_all_services_status(self, key_service, mock_core_key_service):
        """Test getting status for all services."""
        # Arrange
        user_id = "user_123"
        mock_core_key_service.get_api_key_for_service.return_value = None

        # Act
        result = await key_service.get_all_services_status(user_id)

        # Assert
        assert isinstance(result, ApiKeyServicesStatusResponse)
        assert "openai" in result.services
        assert "weather" in result.services
        assert "flights" in result.services
        assert len(result.services) == 8  # All supported services

    async def test_validate_api_key_success(
        self, key_service, mock_core_key_service, sample_validation_result
    ):
        """Test successful API key validation."""
        # Arrange
        user_id = "user_123"
        key_id = "key_123"
        mock_core_key_service.validate_api_key.return_value = sample_validation_result

        # Act
        result = await key_service.validate_api_key(user_id, key_id)

        # Assert
        assert isinstance(result, ApiKeyValidationResponse)
        assert result.is_valid is True
        assert result.service == "openai"
        assert result.message == "API key is valid"

        mock_core_key_service.validate_api_key.assert_called_once_with(key_id, user_id)

    async def test_validate_key_value_success(
        self, key_service, mock_core_key_service, sample_validation_result
    ):
        """Test successful API key value validation."""
        # Arrange
        request = ValidateApiKeyRequest(
            service="openai",
            key_value="sk-test123",
        )
        mock_core_key_service._validate_api_key.return_value = sample_validation_result

        # Act
        result = await key_service.validate_key_value(request)

        # Assert
        assert isinstance(result, ApiKeyValidationResponse)
        assert result.is_valid is True
        assert result.service == "openai"

        mock_core_key_service._validate_api_key.assert_called_once_with(
            request.service, request.key_value
        )

    async def test_validate_key_value_error(self, key_service, mock_core_key_service):
        """Test API key value validation error."""
        # Arrange
        request = ValidateApiKeyRequest(
            service="openai",
            key_value="invalid_key",
        )
        mock_core_key_service._validate_api_key.side_effect = Exception(
            "Validation error"
        )

        # Act
        result = await key_service.validate_key_value(request)

        # Assert
        assert isinstance(result, ApiKeyValidationResponse)
        assert result.is_valid is False
        assert "Validation error" in result.message

    async def test_rotate_api_key_success(
        self, key_service, mock_core_key_service, sample_core_api_key
    ):
        """Test successful API key rotation."""
        # Arrange
        user_id = "user_123"
        key_id = "key_123"
        request = RotateApiKeyRequest(new_key_value="sk-newkey123")

        mock_core_key_service.rotate_api_key.return_value = sample_core_api_key

        # Act
        result = await key_service.rotate_api_key(user_id, key_id, request)

        # Assert
        assert isinstance(result, ApiKeyResponse)
        assert result.id == key_id

        mock_core_key_service.rotate_api_key.assert_called_once_with(
            key_id, user_id, request.new_key_value
        )

    async def test_delete_api_key_success(self, key_service, mock_core_key_service):
        """Test successful API key deletion."""
        # Arrange
        user_id = "user_123"
        key_id = "key_123"
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
        user_id = "user_123"
        key_id = "nonexistent_key"
        mock_core_key_service.delete_api_key.return_value = False

        # Act & Assert
        with pytest.raises(CoreValidationError, match="not found"):
            await key_service.delete_api_key(user_id, key_id)

    async def test_model_adaptation(self, key_service, sample_core_api_key):
        """Test model adaptation between core and API models."""
        # Test API key response adaptation
        api_key = key_service._adapt_api_key_response(sample_core_api_key)

        assert isinstance(api_key, ApiKeyResponse)
        assert api_key.id == sample_core_api_key.id
        assert api_key.name == sample_core_api_key.name
        assert api_key.service == sample_core_api_key.service
        assert api_key.description == sample_core_api_key.description
        assert api_key.is_valid == sample_core_api_key.is_valid
        assert api_key.usage_count == sample_core_api_key.usage_count

    async def test_validation_result_adaptation(
        self, key_service, sample_validation_result
    ):
        """Test validation result adaptation."""
        # Test validation response adaptation
        api_validation = key_service._adapt_validation_response(
            sample_validation_result
        )

        assert isinstance(api_validation, ApiKeyValidationResponse)
        assert api_validation.is_valid == sample_validation_result.is_valid
        assert api_validation.service == sample_validation_result.service
        assert api_validation.message == sample_validation_result.message
        assert api_validation.details == sample_validation_result.details

    async def test_lazy_service_initialization(self):
        """Test that core service is initialized lazily."""
        # Arrange
        key_service = KeyService()

        # Assert - Service should be None initially
        assert key_service.core_key_service is None

        # Act - Access service (would initialize it in real scenario)
        # Note: In real scenario, this would call get_core_key_management_service()
        # Here we just verify the lazy initialization pattern is in place
        assert hasattr(key_service, "_get_core_key_service")

    async def test_error_handling_and_logging(
        self, key_service, mock_core_key_service, caplog
    ):
        """Test error handling and logging."""
        # Arrange
        user_id = "user_123"
        request = CreateApiKeyRequest(
            name="Test Key",
            service="openai",
            key_value="sk-test123",
        )

        mock_core_key_service.create_api_key.side_effect = CoreServiceError(
            "Encryption failed"
        )

        # Act & Assert
        with pytest.raises(CoreServiceError):
            await key_service.create_api_key(user_id, request)

        # Verify logging
        assert "API key creation failed" in caplog.text
