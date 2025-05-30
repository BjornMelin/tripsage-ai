"""
Comprehensive tests for KeyManagementService.

This module provides full test coverage for BYOK (Bring Your Own Key) functionality
including API key validation, storage, rotation, and monitoring.
"""

from datetime import datetime, timedelta, timezone
from enum import Enum
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from tripsage_core.exceptions.exceptions import (
    CoreResourceNotFoundError as NotFoundError,
)
from tripsage_core.exceptions.exceptions import (
    CoreServiceError as ServiceError,
)
from tripsage_core.exceptions.exceptions import (
    CoreValidationError as ValidationError,
)
from tripsage_core.services.business.key_management_service import (
    ApiKeyCreateRequest,
    ApiKeyResponse,
    ApiKeyValidationResult,
    KeyManagementService,
    get_key_management_service,
)


# Define mock enums and classes for testing
class Provider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    AZURE = "azure"


class Status(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"
    SUSPENDED = "suspended"


class Type(str, Enum):
    API_KEY = "api_key"
    SECRET_KEY = "secret_key"
    OAUTH_TOKEN = "oauth_token"


class UpdateRequest:
    def __init__(self, name=None, description=None, tags=None):
        self.name = name
        self.description = description
        self.tags = tags


class Usage:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class KeyRotationRequest:
    def __init__(self, new_key_value, reason=None):
        self.new_key_value = new_key_value
        self.reason = reason


class TestKeyManagementService:
    """Test suite for KeyManagementService."""

    @pytest.fixture
    def mock_database_service(self):
        """Mock database service."""
        db = AsyncMock()
        return db

    @pytest.fixture
    def mock_encryption_service(self):
        """Mock encryption service."""
        encryption = AsyncMock()
        encryption.encrypt.return_value = "encrypted_key_value"
        encryption.decrypt.return_value = "decrypted_key_value"
        return encryption

    @pytest.fixture
    def mock_validator_service(self):
        """Mock key validator service."""
        validator = AsyncMock()
        return validator

    @pytest.fixture
    def key_management_service(
        self, mock_database_service, mock_encryption_service, mock_validator_service
    ):
        """Create KeyManagementService instance with mocked dependencies."""
        return KeyManagementService(
            database_service=mock_database_service,
            encryption_service=mock_encryption_service,
            validator_service=mock_validator_service,
        )

    @pytest.fixture
    def sample_api_key_create_request(self):
        """Sample API key creation request."""
        return ApiKeyCreateRequest(
            name="OpenAI API Key",
            provider=Provider.OPENAI,
            key_type=Type.API_KEY,
            key_value="test_api_key_for_unit_tests",
            description="Key for GPT-4 access",
            expires_at=datetime.now(timezone.utc) + timedelta(days=365),
        )

    @pytest.fixture
    def sample_api_key(self):
        """Sample API key object."""
        key_id = str(uuid4())
        user_id = str(uuid4())
        now = datetime.now(timezone.utc)

        return ApiKeyResponse(
            id=key_id,
            user_id=user_id,
            name="OpenAI API Key",
            provider=Provider.OPENAI,
            key_type=Type.API_KEY,
            key_value_hash="hashed_key_value",
            encrypted_key_value="encrypted_key_value",
            status=Status.ACTIVE,
            description="Key for GPT-4 access",
            created_at=now,
            updated_at=now,
            expires_at=now + timedelta(days=365),
            last_used=None,
            usage_count=0,
            last_validated=now,
            validation_error=None,
            is_primary=False,
            tags=["production", "gpt-4"],
            rate_limit_per_minute=100,
            rate_limit_per_day=10000,
            allowed_endpoints=["chat/completions", "embeddings"],
            restricted_ips=[],
            metadata={"model_access": ["gpt-4", "gpt-3.5-turbo"]},
        )

    async def test_create_api_key_success(
        self,
        key_management_service,
        mock_database_service,
        mock_encryption_service,
        mock_validator_service,
        sample_api_key_create_request,
    ):
        """Test successful API key creation."""
        user_id = str(uuid4())

        # Mock validation success
        mock_validator_service.validate_key.return_value = ApiKeyValidationResult(
            is_valid=True,
            provider_confirmed=Provider.OPENAI,
            available_models=["gpt-4", "gpt-3.5-turbo"],
            rate_limits={"rpm": 100, "rpd": 10000},
        )

        # Mock database operations
        mock_database_service.get_user_api_keys_count.return_value = 2
        mock_database_service.store_api_key.return_value = None

        result = await key_management_service.create_api_key(
            user_id, sample_api_key_create_request
        )

        # Assertions
        assert result.user_id == user_id
        assert result.name == sample_api_key_create_request.name
        assert result.provider == sample_api_key_create_request.provider
        assert result.status == Status.ACTIVE
        assert result.encrypted_key_value == "encrypted_key_value"

        # Verify service calls
        mock_validator_service.validate_key.assert_called_once()
        mock_encryption_service.encrypt.assert_called_once()
        mock_database_service.store_api_key.assert_called_once()

    async def test_create_api_key_validation_failed(
        self,
        key_management_service,
        mock_validator_service,
        sample_api_key_create_request,
    ):
        """Test API key creation with validation failure."""
        user_id = str(uuid4())

        # Mock validation failure
        mock_validator_service.validate_key.return_value = ApiKeyValidationResult(
            is_valid=False, error_message="Invalid API key format"
        )

        with pytest.raises(ValidationError, match="API key validation failed"):
            await key_management_service.create_api_key(
                user_id, sample_api_key_create_request
            )

    async def test_create_api_key_limit_exceeded(
        self,
        key_management_service,
        mock_database_service,
        sample_api_key_create_request,
    ):
        """Test API key creation when user limit exceeded."""
        user_id = str(uuid4())

        # Mock key count at limit
        mock_database_service.get_user_api_keys_count.return_value = (
            key_management_service.max_keys_per_user
        )

        with pytest.raises(ValidationError, match="Maximum number of API keys reached"):
            await key_management_service.create_api_key(
                user_id, sample_api_key_create_request
            )

    async def test_get_api_key_success(
        self, key_management_service, mock_database_service, sample_api_key
    ):
        """Test successful API key retrieval."""
        mock_database_service.get_api_key.return_value = sample_api_key.model_dump()

        result = await key_management_service.get_api_key(
            sample_api_key.id, sample_api_key.user_id
        )

        assert result is not None
        assert result.id == sample_api_key.id
        assert result.user_id == sample_api_key.user_id
        mock_database_service.get_api_key.assert_called_once()

    async def test_get_api_key_not_found(
        self, key_management_service, mock_database_service
    ):
        """Test API key retrieval when key doesn't exist."""
        key_id = str(uuid4())
        user_id = str(uuid4())

        mock_database_service.get_api_key.return_value = None

        result = await key_management_service.get_api_key(key_id, user_id)

        assert result is None

    async def test_get_api_key_access_denied(
        self, key_management_service, mock_database_service, sample_api_key
    ):
        """Test API key retrieval with access denied."""
        different_user_id = str(uuid4())

        mock_database_service.get_api_key.return_value = sample_api_key.model_dump()

        result = await key_management_service.get_api_key(
            sample_api_key.id, different_user_id
        )

        assert result is None

    async def test_list_api_keys_success(
        self, key_management_service, mock_database_service, sample_api_key
    ):
        """Test successful API keys listing."""
        user_id = str(uuid4())

        mock_database_service.get_user_api_keys.return_value = [
            sample_api_key.model_dump()
        ]

        results = await key_management_service.list_api_keys(user_id)

        assert len(results) == 1
        assert results[0].id == sample_api_key.id
        mock_database_service.get_user_api_keys.assert_called_once()

    async def test_update_api_key_success(
        self, key_management_service, mock_database_service, sample_api_key
    ):
        """Test successful API key update."""
        mock_database_service.get_api_key.return_value = sample_api_key.model_dump()
        mock_database_service.update_api_key.return_value = None

        update_request = UpdateRequest(
            name="Updated OpenAI Key",
            description="Updated description",
            tags=["production", "updated"],
        )

        result = await key_management_service.update_api_key(
            sample_api_key.id, sample_api_key.user_id, update_request
        )

        assert result.name == "Updated OpenAI Key"
        assert result.description == "Updated description"
        assert result.tags == ["production", "updated"]
        assert result.updated_at > sample_api_key.updated_at

        mock_database_service.update_api_key.assert_called_once()

    async def test_update_api_key_not_found(
        self, key_management_service, mock_database_service
    ):
        """Test API key update when key doesn't exist."""
        key_id = str(uuid4())
        user_id = str(uuid4())

        mock_database_service.get_api_key.return_value = None

        update_request = UpdateRequest(name="Updated Key")

        with pytest.raises(NotFoundError, match="API key not found"):
            await key_management_service.update_api_key(key_id, user_id, update_request)

    async def test_delete_api_key_success(
        self, key_management_service, mock_database_service, sample_api_key
    ):
        """Test successful API key deletion."""
        mock_database_service.get_api_key.return_value = sample_api_key.model_dump()
        mock_database_service.delete_api_key.return_value = True

        result = await key_management_service.delete_api_key(
            sample_api_key.id, sample_api_key.user_id
        )

        assert result is True
        mock_database_service.delete_api_key.assert_called_once()

    async def test_delete_api_key_not_found(
        self, key_management_service, mock_database_service
    ):
        """Test API key deletion when key doesn't exist."""
        key_id = str(uuid4())
        user_id = str(uuid4())

        mock_database_service.get_api_key.return_value = None

        with pytest.raises(NotFoundError, match="API key not found"):
            await key_management_service.delete_api_key(key_id, user_id)

    async def test_validate_api_key_success(
        self,
        key_management_service,
        mock_database_service,
        mock_validator_service,
        sample_api_key,
    ):
        """Test successful API key validation."""
        mock_database_service.get_api_key.return_value = sample_api_key.model_dump()
        mock_database_service.update_api_key.return_value = None

        # Mock validation success
        mock_validator_service.validate_key.return_value = ApiKeyValidationResult(
            is_valid=True,
            provider_confirmed=Provider.OPENAI,
            available_models=["gpt-4"],
            rate_limits={"rpm": 100},
        )

        result = await key_management_service.validate_api_key(
            sample_api_key.id, sample_api_key.user_id
        )

        assert result.is_valid is True
        assert result.provider_confirmed == Provider.OPENAI
        mock_validator_service.validate_key.assert_called_once()

    async def test_validate_api_key_failed(
        self,
        key_management_service,
        mock_database_service,
        mock_validator_service,
        sample_api_key,
    ):
        """Test API key validation failure."""
        mock_database_service.get_api_key.return_value = sample_api_key.model_dump()
        mock_database_service.update_api_key.return_value = None

        # Mock validation failure
        mock_validator_service.validate_key.return_value = ApiKeyValidationResult(
            is_valid=False, error_message="Key has been revoked"
        )

        result = await key_management_service.validate_api_key(
            sample_api_key.id, sample_api_key.user_id
        )

        assert result.is_valid is False
        assert "Key has been revoked" in result.error_message

    async def test_rotate_api_key_success(
        self,
        key_management_service,
        mock_database_service,
        mock_encryption_service,
        mock_validator_service,
        sample_api_key,
    ):
        """Test successful API key rotation."""
        mock_database_service.get_api_key.return_value = sample_api_key.model_dump()
        mock_database_service.update_api_key.return_value = None

        # Mock validation for new key
        mock_validator_service.validate_key.return_value = ApiKeyValidationResult(
            is_valid=True, provider_confirmed=Provider.OPENAI
        )

        rotation_request = KeyRotationRequest(
            new_key_value="test_new_key_for_rotation", reason="Security rotation"
        )

        result = await key_management_service.rotate_api_key(
            sample_api_key.id, sample_api_key.user_id, rotation_request
        )

        assert result.encrypted_key_value == "encrypted_key_value"
        assert result.updated_at > sample_api_key.updated_at

        # Verify services called
        mock_validator_service.validate_key.assert_called_once()
        mock_encryption_service.encrypt.assert_called_once()
        mock_database_service.update_api_key.assert_called_once()

    async def test_get_api_key_usage_success(
        self, key_management_service, mock_database_service, sample_api_key
    ):
        """Test successful API key usage retrieval."""
        usage_data = {
            "api_key_id": sample_api_key.id,
            "total_requests": 1500,
            "successful_requests": 1450,
            "failed_requests": 50,
            "total_tokens_used": 75000,
            "cost_incurred": 15.50,
            "first_used": datetime.now(timezone.utc) - timedelta(days=30),
            "last_used": datetime.now(timezone.utc) - timedelta(hours=1),
            "usage_by_endpoint": {"chat/completions": 1200, "embeddings": 300},
            "usage_by_day": {},
            "rate_limit_hits": 5,
            "quota_exceeded_count": 0,
        }

        mock_database_service.get_api_key_usage.return_value = usage_data

        result = await key_management_service.get_api_key_usage(
            sample_api_key.id, sample_api_key.user_id
        )

        assert isinstance(result, Usage)
        assert result.total_requests == 1500
        assert result.successful_requests == 1450
        assert result.cost_incurred == 15.50

    async def test_record_api_key_usage_success(
        self, key_management_service, mock_database_service
    ):
        """Test successful API key usage recording."""
        key_id = str(uuid4())
        usage_data = {
            "endpoint": "chat/completions",
            "tokens_used": 100,
            "cost": 0.002,
            "success": True,
            "response_time": 1.5,
        }

        mock_database_service.record_api_key_usage.return_value = None

        await key_management_service.record_api_key_usage(key_id, usage_data)

        mock_database_service.record_api_key_usage.assert_called_once_with(
            key_id, usage_data
        )

    async def test_set_primary_key_success(
        self, key_management_service, mock_database_service, sample_api_key
    ):
        """Test successful primary key setting."""
        mock_database_service.get_api_key.return_value = sample_api_key.model_dump()
        mock_database_service.set_primary_api_key.return_value = None

        result = await key_management_service.set_primary_key(
            sample_api_key.id, sample_api_key.user_id, Provider.OPENAI
        )

        assert result is True
        mock_database_service.set_primary_api_key.assert_called_once()

    async def test_get_primary_key_success(
        self, key_management_service, mock_database_service, sample_api_key
    ):
        """Test successful primary key retrieval."""
        primary_key_data = sample_api_key.model_dump()
        primary_key_data["is_primary"] = True

        mock_database_service.get_primary_api_key.return_value = primary_key_data

        result = await key_management_service.get_primary_key(
            sample_api_key.user_id, Provider.OPENAI
        )

        assert result is not None
        assert result.is_primary is True
        assert result.provider == Provider.OPENAI

    async def test_deactivate_api_key_success(
        self, key_management_service, mock_database_service, sample_api_key
    ):
        """Test successful API key deactivation."""
        mock_database_service.get_api_key.return_value = sample_api_key.model_dump()
        mock_database_service.update_api_key.return_value = None

        result = await key_management_service.deactivate_api_key(
            sample_api_key.id, sample_api_key.user_id, reason="Security concerns"
        )

        assert result.status == Status.INACTIVE
        mock_database_service.update_api_key.assert_called_once()

    async def test_reactivate_api_key_success(
        self,
        key_management_service,
        mock_database_service,
        mock_validator_service,
        sample_api_key,
    ):
        """Test successful API key reactivation."""
        # Set key as inactive
        sample_api_key.status = Status.INACTIVE

        mock_database_service.get_api_key.return_value = sample_api_key.model_dump()
        mock_database_service.update_api_key.return_value = None

        # Mock successful validation
        mock_validator_service.validate_key.return_value = ApiKeyValidationResult(
            is_valid=True, provider_confirmed=Provider.OPENAI
        )

        result = await key_management_service.reactivate_api_key(
            sample_api_key.id, sample_api_key.user_id
        )

        assert result.status == Status.ACTIVE
        mock_validator_service.validate_key.assert_called_once()

    async def test_get_user_key_statistics_success(
        self, key_management_service, mock_database_service
    ):
        """Test successful user key statistics retrieval."""
        user_id = str(uuid4())

        stats_data = {
            "total_keys": 5,
            "active_keys": 4,
            "inactive_keys": 1,
            "keys_by_provider": {"openai": 3, "anthropic": 2},
            "total_usage_last_30_days": 50000,
            "total_cost_last_30_days": 125.75,
            "most_used_key_id": str(uuid4()),
        }

        mock_database_service.get_user_key_statistics.return_value = stats_data

        result = await key_management_service.get_user_key_statistics(user_id)

        assert result["total_keys"] == 5
        assert result["active_keys"] == 4
        assert result["total_cost_last_30_days"] == 125.75

    async def test_bulk_validate_keys_success(
        self, key_management_service, mock_database_service, mock_validator_service
    ):
        """Test successful bulk key validation."""
        user_id = str(uuid4())

        # Mock multiple keys
        keys_data = [
            {"id": str(uuid4()), "provider": "openai", "key_value": "key1"},
            {"id": str(uuid4()), "provider": "anthropic", "key_value": "key2"},
        ]

        mock_database_service.get_user_api_keys.return_value = keys_data
        mock_database_service.update_api_key.return_value = None

        # Mock validation results
        mock_validator_service.validate_key.side_effect = [
            ApiKeyValidationResult(is_valid=True, provider_confirmed=Provider.OPENAI),
            ApiKeyValidationResult(is_valid=False, error_message="Invalid key"),
        ]

        results = await key_management_service.bulk_validate_keys(user_id)

        assert len(results) == 2
        assert results[0]["is_valid"] is True
        assert results[1]["is_valid"] is False

    async def test_cleanup_expired_keys_success(
        self, key_management_service, mock_database_service
    ):
        """Test successful cleanup of expired keys."""
        mock_database_service.cleanup_expired_api_keys.return_value = 3

        result = await key_management_service.cleanup_expired_keys()

        assert result == 3
        mock_database_service.cleanup_expired_api_keys.assert_called_once()

    def test_hash_key_value(self, key_management_service):
        """Test key value hashing."""
        key_value = "test_key_rotation"
        hashed = key_management_service._hash_key_value(key_value)

        assert hashed != key_value
        assert len(hashed) == 64  # SHA256 hex length

        # Same input should produce same hash
        hashed2 = key_management_service._hash_key_value(key_value)
        assert hashed == hashed2

    def test_mask_key_value(self, key_management_service):
        """Test key value masking for display."""
        key_value = "test_key_validation_for_unit_tests"
        masked = key_management_service._mask_key_value(key_value)

        assert masked.startswith("sk-")
        assert "****" in masked
        assert masked.endswith("cdef")
        assert len(masked) < len(key_value)

    async def test_service_error_handling(
        self,
        key_management_service,
        mock_database_service,
        sample_api_key_create_request,
    ):
        """Test service error handling."""
        user_id = str(uuid4())

        # Mock database to raise an exception
        mock_database_service.get_user_api_keys_count.side_effect = Exception(
            "Database error"
        )

        with pytest.raises(ServiceError, match="Failed to create API key"):
            await key_management_service.create_api_key(
                user_id, sample_api_key_create_request
            )

    def test_get_key_management_service_dependency(self):
        """Test the dependency injection function."""
        service = get_key_management_service()
        assert isinstance(service, KeyManagementService)

    async def test_rate_limit_checking(
        self, key_management_service, mock_database_service, sample_api_key
    ):
        """Test rate limit checking for API keys."""
        mock_database_service.get_api_key_rate_limit_usage.return_value = {
            "requests_this_minute": 95,
            "requests_today": 9500,
        }

        # Should be within limits
        is_within_limits = await key_management_service._check_rate_limits(
            sample_api_key
        )
        assert is_within_limits is True

        # Mock exceeding limits
        mock_database_service.get_api_key_rate_limit_usage.return_value = {
            "requests_this_minute": 105,  # Exceeds limit of 100
            "requests_today": 9500,
        }

        is_within_limits = await key_management_service._check_rate_limits(
            sample_api_key
        )
        assert is_within_limits is False

    async def test_key_expiration_notification(
        self, key_management_service, mock_database_service
    ):
        """Test key expiration notification."""
        # Mock keys expiring soon
        expiring_keys = [
            {
                "id": str(uuid4()),
                "name": "Expiring Key",
                "expires_at": datetime.now(timezone.utc) + timedelta(days=5),
                "user_id": str(uuid4()),
            }
        ]

        mock_database_service.get_keys_expiring_soon.return_value = expiring_keys

        notifications = await key_management_service.get_expiration_notifications(
            days_ahead=7
        )

        assert len(notifications) == 1
        assert "expiring" in notifications[0]["message"].lower()

    async def test_key_security_audit(
        self, key_management_service, mock_database_service
    ):
        """Test key security audit functionality."""
        user_id = str(uuid4())

        audit_results = {
            "total_keys_checked": 5,
            "weak_keys": 1,
            "expired_keys": 0,
            "unused_keys": 2,
            "keys_without_restrictions": 1,
            "recommendations": [
                "Consider adding IP restrictions to production keys",
                "Rotate keys that haven't been used in 90+ days",
            ],
        }

        mock_database_service.audit_user_keys.return_value = audit_results

        result = await key_management_service.audit_user_keys(user_id)

        assert result["total_keys_checked"] == 5
        assert len(result["recommendations"]) == 2
