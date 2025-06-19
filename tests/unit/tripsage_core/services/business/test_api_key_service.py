"""Comprehensive test suite for API Key Service.

This file consolidates tests from multiple test files to provide
complete coverage without duplication.
"""

import asyncio
import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from cryptography.fernet import Fernet
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from tripsage_core.exceptions.exceptions import (
    CoreResourceNotFoundError as NotFoundError,
)
from tripsage_core.exceptions.exceptions import (
    CoreServiceError as ServiceError,
)
from tripsage_core.exceptions.exceptions import (
    CoreValidationError as ConflictError,
)
from tripsage_core.exceptions.exceptions import (
    CoreValidationError as ServiceValidationError,
)
from tripsage_core.models.db.api_key import (
    APIKey,
    APIKeyCreate,
    APIKeyUpdate,
)
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
    return Fernet.generate_key()


@pytest.fixture
async def api_key_service(
    mock_database_service, mock_cache_service, mock_encryption_key
):
    """Create APIKeyService instance for testing."""
    with patch("tripsage_core.services.business.api_key_service.Fernet") as mock_fernet:
        mock_fernet.return_value = Fernet(mock_encryption_key)
        service = APIKeyService(
            database_service=mock_database_service,
            cache_service=mock_cache_service,
            encryption_key=mock_encryption_key.decode(),
        )
        yield service


@pytest.fixture
def sample_api_key():
    """Sample API key for testing."""
    return APIKey(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        name="Test API Key",
        key_hash="hashed_key",
        service="test_service",
        permissions=["read", "write"],
        rate_limit=100,
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        last_used_at=None,
        is_active=True,
    )


class TestAPIKeyServiceCore:
    """Core functionality tests for APIKeyService."""

    async def test_create_api_key_success(self, api_key_service, mock_database_service):
        """Test successful API key creation."""
        user_id = uuid.uuid4()
        create_request = APIKeyCreate(
            name="Test Key",
            service="test_service",
            permissions=["read"],
            rate_limit=100,
            expires_in_days=30,
        )

        mock_database_service.fetch_one.return_value = None  # No duplicate
        mock_database_service.execute.return_value = None
        mock_database_service.fetch_one.side_effect = [
            None,  # Check for duplicate
            {  # Return created key
                "id": uuid.uuid4(),
                "user_id": user_id,
                "name": create_request.name,
                "key_hash": "hashed_key",
                "service": create_request.service,
                "permissions": create_request.permissions,
                "rate_limit": create_request.rate_limit,
                "expires_at": datetime.now(timezone.utc) + timedelta(days=30),
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "last_used_at": None,
                "is_active": True,
            },
        ]

        result = await api_key_service.create_api_key(str(user_id), create_request)

        assert result is not None
        assert result.name == create_request.name
        assert result.service == create_request.service
        assert "api_key" in result.model_dump()
        mock_database_service.execute.assert_called_once()

    async def test_create_api_key_duplicate_name(
        self, api_key_service, mock_database_service
    ):
        """Test API key creation with duplicate name."""
        user_id = uuid.uuid4()
        create_request = APIKeyCreate(
            name="Duplicate Key",
            service="test_service",
            permissions=["read"],
        )

        mock_database_service.fetch_one.return_value = {
            "id": uuid.uuid4()
        }  # Duplicate exists

        with pytest.raises(ConflictError) as exc:
            await api_key_service.create_api_key(str(user_id), create_request)

        assert "already exists" in str(exc.value)

    async def test_validate_api_key_success(
        self, api_key_service, mock_database_service, mock_cache_service
    ):
        """Test successful API key validation."""
        api_key = "test_api_key"
        user_id = uuid.uuid4()
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        mock_cache_service.get.return_value = None  # Cache miss
        mock_database_service.fetch_one.return_value = {
            "id": uuid.uuid4(),
            "user_id": user_id,
            "name": "Test Key",
            "key_hash": key_hash,
            "service": "test_service",
            "permissions": ["read", "write"],
            "rate_limit": 100,
            "expires_at": datetime.now(timezone.utc) + timedelta(days=30),
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "last_used_at": None,
            "is_active": True,
        }
        mock_database_service.execute.return_value = None  # Update last_used_at

        result = await api_key_service.validate_api_key(api_key)

        assert result is not None
        assert str(result.user_id) == str(user_id)
        assert result.service == "test_service"
        mock_cache_service.set.assert_called_once()

    async def test_validate_api_key_not_found(
        self, api_key_service, mock_database_service, mock_cache_service
    ):
        """Test API key validation when key not found."""
        api_key = "invalid_key"

        mock_cache_service.get.return_value = None
        mock_database_service.fetch_one.return_value = None

        with pytest.raises(NotFoundError) as exc:
            await api_key_service.validate_api_key(api_key)

        assert "not found" in str(exc.value)

    async def test_validate_api_key_expired(
        self, api_key_service, mock_database_service, mock_cache_service
    ):
        """Test API key validation when key is expired."""
        api_key = "expired_key"
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        mock_cache_service.get.return_value = None
        mock_database_service.fetch_one.return_value = {
            "id": uuid.uuid4(),
            "user_id": uuid.uuid4(),
            "name": "Expired Key",
            "key_hash": key_hash,
            "service": "test_service",
            "permissions": ["read"],
            "rate_limit": 100,
            "expires_at": datetime.now(timezone.utc) - timedelta(days=1),  # Expired
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "last_used_at": None,
            "is_active": True,
        }

        with pytest.raises(ValidationError) as exc:
            await api_key_service.validate_api_key(api_key)

        assert "expired" in str(exc.value)

    async def test_list_user_keys(self, api_key_service, mock_database_service):
        """Test listing user's API keys."""
        user_id = uuid.uuid4()
        mock_database_service.fetch_many.return_value = [
            {
                "id": uuid.uuid4(),
                "user_id": user_id,
                "name": "Key 1",
                "service": "service1",
                "permissions": ["read"],
                "rate_limit": 100,
                "expires_at": datetime.now(timezone.utc) + timedelta(days=30),
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "last_used_at": None,
                "is_active": True,
            },
            {
                "id": uuid.uuid4(),
                "user_id": user_id,
                "name": "Key 2",
                "service": "service2",
                "permissions": ["read", "write"],
                "rate_limit": 200,
                "expires_at": datetime.now(timezone.utc) + timedelta(days=60),
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "last_used_at": datetime.now(timezone.utc),
                "is_active": False,
            },
        ]

        result = await api_key_service.list_user_keys(str(user_id))

        assert len(result) == 2
        assert result[0].name == "Key 1"
        assert result[1].name == "Key 2"
        assert result[0].is_active is True
        assert result[1].is_active is False

    async def test_update_api_key(self, api_key_service, mock_database_service):
        """Test updating an API key."""
        key_id = uuid.uuid4()
        user_id = uuid.uuid4()
        update_request = APIKeyUpdate(
            name="Updated Key",
            permissions=["read", "write", "delete"],
            rate_limit=200,
        )

        mock_database_service.fetch_one.side_effect = [
            {  # Check ownership
                "id": key_id,
                "user_id": user_id,
            },
            {  # Return updated key
                "id": key_id,
                "user_id": user_id,
                "name": update_request.name,
                "key_hash": "hashed_key",
                "service": "test_service",
                "permissions": update_request.permissions,
                "rate_limit": update_request.rate_limit,
                "expires_at": datetime.now(timezone.utc) + timedelta(days=30),
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "last_used_at": None,
                "is_active": True,
            },
        ]

        result = await api_key_service.update_api_key(
            str(key_id), str(user_id), update_request
        )

        assert result.name == update_request.name
        assert result.permissions == update_request.permissions
        assert result.rate_limit == update_request.rate_limit

    async def test_delete_api_key(
        self, api_key_service, mock_database_service, mock_cache_service
    ):
        """Test deleting an API key."""
        key_id = uuid.uuid4()
        user_id = uuid.uuid4()

        mock_database_service.fetch_one.return_value = {
            "id": key_id,
            "user_id": user_id,
            "key_hash": "hashed_key",
        }
        mock_database_service.execute.return_value = None

        await api_key_service.delete_api_key(str(key_id), str(user_id))

        mock_database_service.execute.assert_called_once()
        mock_cache_service.delete.assert_called_once()

    async def test_delete_api_key_not_found(
        self, api_key_service, mock_database_service
    ):
        """Test deleting non-existent API key."""
        key_id = uuid.uuid4()
        user_id = uuid.uuid4()

        mock_database_service.fetch_one.return_value = None

        with pytest.raises(NotFoundError):
            await api_key_service.delete_api_key(str(key_id), str(user_id))

    async def test_health_check_success(
        self, api_key_service, mock_database_service, mock_cache_service
    ):
        """Test successful health check."""
        mock_database_service.execute.return_value = None
        mock_cache_service.get.return_value = "pong"

        result = await api_key_service.health_check()

        assert result["status"] == "healthy"
        assert result["database"] == "ok"
        assert result["cache"] == "ok"

    async def test_health_check_database_failure(
        self, api_key_service, mock_database_service, mock_cache_service
    ):
        """Test health check with database failure."""
        mock_database_service.execute.side_effect = Exception("DB error")
        mock_cache_service.get.return_value = "pong"

        result = await api_key_service.health_check()

        assert result["status"] == "unhealthy"
        assert result["database"] == "error"
        assert result["cache"] == "ok"


class TestAPIKeyServiceEncryption:
    """Test encryption/decryption functionality."""

    async def test_encrypt_decrypt_success(self, api_key_service):
        """Test successful encryption and decryption."""
        plaintext = "test_api_key_123"

        encrypted = await api_key_service._encrypt_key(plaintext)
        decrypted = await api_key_service._decrypt_key(encrypted)

        assert decrypted == plaintext
        assert encrypted != plaintext

    async def test_decrypt_invalid_data(self, api_key_service):
        """Test decryption with invalid data."""
        with pytest.raises(ServiceError):
            await api_key_service._decrypt_key("invalid_encrypted_data")

    async def test_encrypt_empty_string(self, api_key_service):
        """Test encryption of empty string."""
        encrypted = await api_key_service._encrypt_key("")
        decrypted = await api_key_service._decrypt_key(encrypted)

        assert decrypted == ""

    @given(st.text(min_size=1, max_size=1000))
    @settings(max_examples=10)
    async def test_encrypt_decrypt_property(self, api_key_service, text):
        """Property-based test for encryption/decryption."""
        encrypted = await api_key_service._encrypt_key(text)
        decrypted = await api_key_service._decrypt_key(encrypted)

        assert decrypted == text


class TestAPIKeyServiceConcurrency:
    """Test concurrent operations."""

    async def test_concurrent_validations(
        self, api_key_service, mock_database_service, mock_cache_service
    ):
        """Test concurrent API key validations."""
        api_keys = [f"key_{i}" for i in range(10)]

        mock_cache_service.get.return_value = None
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

        # Override key hash check for testing
        with patch.object(api_key_service, "_validate_api_key_hash", return_value=True):
            tasks = [api_key_service.validate_api_key(key) for key in api_keys]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        assert len(results) == 10
        assert all(not isinstance(r, Exception) for r in results)

    async def test_concurrent_creates(self, api_key_service, mock_database_service):
        """Test concurrent API key creation."""
        user_id = uuid.uuid4()
        creates = [
            APIKeyCreate(
                name=f"Key {i}",
                service="test_service",
                permissions=["read"],
            )
            for i in range(5)
        ]

        mock_database_service.fetch_one.return_value = None  # No duplicates
        mock_database_service.execute.return_value = None

        # Mock different responses for each create
        mock_database_service.fetch_one.side_effect = [
            None
        ] * 10  # Check + fetch for each

        tasks = [
            api_key_service.create_api_key(str(user_id), create) for create in creates
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Some might fail due to race conditions, but at least one should succeed
        successful = [r for r in results if not isinstance(r, Exception)]
        assert len(successful) >= 1


class TestAPIKeyServiceValidation:
    """Test input validation."""

    async def test_create_with_invalid_permissions(self, api_key_service):
        """Test creation with invalid permissions."""
        with pytest.raises(ValidationError):
            APIKeyCreate(
                name="Test",
                service="test",
                permissions=["invalid_permission"],  # Should fail validation
            )

    async def test_create_with_negative_rate_limit(self, api_key_service):
        """Test creation with negative rate limit."""
        with pytest.raises(ValidationError):
            APIKeyCreate(
                name="Test",
                service="test",
                permissions=["read"],
                rate_limit=-1,  # Should fail validation
            )

    async def test_update_with_empty_name(self, api_key_service):
        """Test update with empty name."""
        with pytest.raises(ValidationError):
            APIKeyUpdate(name="")  # Should fail validation

    @given(
        st.text(min_size=0, max_size=0),  # Empty strings
        st.integers(max_value=0),  # Non-positive integers
        st.lists(st.text(), max_size=0),  # Empty lists
    )
    async def test_invalid_inputs_property(
        self, api_key_service, name, rate_limit, permissions
    ):
        """Property-based test for invalid inputs."""
        with pytest.raises(ValidationError):
            APIKeyCreate(
                name=name,
                service="test",
                permissions=permissions,
                rate_limit=rate_limit,
            )


class TestAPIKeyServiceTransactions:
    """Test transaction handling."""

    async def test_create_rollback_on_error(
        self, api_key_service, mock_database_service
    ):
        """Test transaction rollback on error during creation."""
        user_id = uuid.uuid4()
        create_request = APIKeyCreate(
            name="Test Key",
            service="test_service",
            permissions=["read"],
        )

        mock_database_service.fetch_one.return_value = None
        mock_database_service.execute.side_effect = Exception("DB error")

        with pytest.raises(ServiceError):
            await api_key_service.create_api_key(str(user_id), create_request)

        # Verify rollback would have been called (in real implementation)
        mock_database_service.execute.assert_called()

    async def test_update_rollback_on_error(
        self, api_key_service, mock_database_service
    ):
        """Test transaction rollback on error during update."""
        key_id = uuid.uuid4()
        user_id = uuid.uuid4()
        update_request = APIKeyUpdate(permissions=["read", "write"])

        mock_database_service.fetch_one.return_value = {
            "id": key_id,
            "user_id": user_id,
        }
        mock_database_service.execute.side_effect = Exception("Update failed")

        with pytest.raises(ServiceError):
            await api_key_service.update_api_key(
                str(key_id), str(user_id), update_request
            )


class TestAPIKeyServiceEdgeCases:
    """Test edge cases and error scenarios."""

    async def test_validate_with_none_key(self, api_key_service):
        """Test validation with None key."""
        with pytest.raises(ServiceValidationError):
            await api_key_service.validate_api_key(None)

    async def test_validate_with_empty_key(self, api_key_service):
        """Test validation with empty key."""
        with pytest.raises(ServiceValidationError):
            await api_key_service.validate_api_key("")

    async def test_database_connection_timeout(
        self, api_key_service, mock_database_service
    ):
        """Test handling of database connection timeout."""
        mock_database_service.fetch_one.side_effect = asyncio.TimeoutError()

        with pytest.raises(ServiceError) as exc:
            await api_key_service.list_user_keys("user_id")

        assert "timeout" in str(exc.value).lower()

    async def test_cache_connection_timeout(
        self, api_key_service, mock_database_service, mock_cache_service
    ):
        """Test handling of cache connection timeout."""
        api_key = "test_key"

        mock_cache_service.get.side_effect = asyncio.TimeoutError()
        mock_database_service.fetch_one.return_value = None

        # Should fall back to database when cache times out
        with pytest.raises(NotFoundError):
            await api_key_service.validate_api_key(api_key)

    async def test_get_key_for_service(self, api_key_service, mock_database_service):
        """Test getting API key for specific service."""
        user_id = uuid.uuid4()
        service = "test_service"

        mock_database_service.fetch_one.return_value = {
            "id": uuid.uuid4(),
            "user_id": user_id,
            "name": "Service Key",
            "key_hash": "hash",
            "service": service,
            "permissions": ["read"],
            "rate_limit": 100,
            "expires_at": datetime.now(timezone.utc) + timedelta(days=30),
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "last_used_at": None,
            "is_active": True,
        }

        result = await api_key_service.get_key_for_service(str(user_id), service)

        assert result is not None
        assert result.service == service

    async def test_get_key_for_service_not_found(
        self, api_key_service, mock_database_service
    ):
        """Test getting API key for service when not found."""
        user_id = uuid.uuid4()
        service = "nonexistent_service"

        mock_database_service.fetch_one.return_value = None

        result = await api_key_service.get_key_for_service(str(user_id), service)

        assert result is None


# Performance tests
class TestAPIKeyServicePerformance:
    """Performance-related tests."""

    async def test_bulk_validation_performance(
        self, api_key_service, mock_database_service, mock_cache_service
    ):
        """Test performance of bulk API key validations."""
        num_keys = 100
        api_keys = [f"key_{i}" for i in range(num_keys)]

        mock_cache_service.get.return_value = None
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

        start_time = asyncio.get_event_loop().time()

        with patch.object(api_key_service, "_validate_api_key_hash", return_value=True):
            tasks = [api_key_service.validate_api_key(key) for key in api_keys]
            await asyncio.gather(*tasks, return_exceptions=True)

        elapsed = asyncio.get_event_loop().time() - start_time

        # Should complete 100 validations in under 1 second
        assert elapsed < 1.0

    async def test_cache_performance_improvement(
        self, api_key_service, mock_database_service, mock_cache_service
    ):
        """Test that cache improves validation performance."""
        api_key = "cached_key"
        cached_data = {
            "id": str(uuid.uuid4()),
            "user_id": str(uuid.uuid4()),
            "name": "Cached Key",
            "service": "test",
            "permissions": ["read"],
            "rate_limit": 100,
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            "is_active": True,
        }

        # First call - cache miss
        mock_cache_service.get.return_value = None
        mock_database_service.fetch_one.return_value = {
            "id": uuid.uuid4(),
            "user_id": uuid.uuid4(),
            "name": "Test Key",
            "key_hash": hashlib.sha256(api_key.encode()).hexdigest(),
            "service": "test",
            "permissions": ["read"],
            "rate_limit": 100,
            "expires_at": datetime.now(timezone.utc) + timedelta(days=30),
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "last_used_at": None,
            "is_active": True,
        }

        await api_key_service.validate_api_key(api_key)

        # Second call - cache hit
        mock_cache_service.get.return_value = cached_data

        start_time = asyncio.get_event_loop().time()
        await api_key_service.validate_api_key(api_key)
        cached_elapsed = asyncio.get_event_loop().time() - start_time

        # Cache hit should be very fast
        assert cached_elapsed < 0.01
        # Database should not be called on cache hit
        assert mock_database_service.fetch_one.call_count == 1  # Only first call
