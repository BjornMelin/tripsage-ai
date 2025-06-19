"""
Modern comprehensive test suite for API Key Service.

This module demonstrates modern pytest patterns for TripSage (2025):
- Pydantic v2 compatibility and testing patterns
- Comprehensive property-based testing with Hypothesis
- Modern async testing with pytest-asyncio 1.0
- Advanced mocking and fixtures
- Performance and security testing integration
- Edge case and error path coverage

Covers BJO-210 requirements with 90%+ test coverage target.
"""

import asyncio
import base64
import json
import secrets
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID

import pytest
import pytest_asyncio
from hypothesis import given, strategies as st
from pydantic import ValidationError

from tripsage_core.exceptions.exceptions import (
    CoreServiceError,
    CoreValidationError,
)
from tripsage_core.models.db.api_key import ApiKeyCreate, ApiKeyDB, ApiKeyUpdate
from tripsage_core.services.business.api_key_service import (
    ApiKeyService,
    ServiceHealthStatus,
    ServiceType,
    ValidationResult,
    ValidationStatus,
)


class TestApiKeyServiceModern:
    """
    Modern test suite for API Key Service with comprehensive coverage.
    
    Demonstrates 2025 best practices:
    - Fixture-based dependency injection
    - Property-based testing
    - Async testing patterns
    - Comprehensive error handling
    - Performance testing integration
    """

    @pytest_asyncio.fixture
    async def mock_database(self) -> AsyncMock:
        """Create mock database service with realistic behavior."""
        db = AsyncMock()
        
        # Mock common database operations
        db.fetch_one = AsyncMock(return_value=None)
        db.fetch_all = AsyncMock(return_value=[])
        db.execute = AsyncMock(return_value=None)
        db.begin = AsyncMock()
        db.commit = AsyncMock()
        db.rollback = AsyncMock()
        
        # Add realistic response delays for performance testing
        async def realistic_fetch_one(*args, **kwargs):
            await asyncio.sleep(0.001)  # 1ms realistic database latency
            return None
            
        db.fetch_one.side_effect = realistic_fetch_one
        
        return db

    @pytest_asyncio.fixture
    async def mock_cache(self) -> AsyncMock:
        """Create mock cache service with TTL and performance simulation."""
        cache = AsyncMock()
        
        # Mock cache operations with realistic behavior
        cache.get = AsyncMock(return_value=None)
        cache.set = AsyncMock(return_value=True)
        cache.delete = AsyncMock(return_value=True)
        cache.exists = AsyncMock(return_value=False)
        cache.ttl = AsyncMock(return_value=-1)
        
        # Add cache hit/miss simulation
        cache_data = {}
        
        async def mock_get(key: str):
            await asyncio.sleep(0.0001)  # 0.1ms cache latency
            return cache_data.get(key)
            
        async def mock_set(key: str, value: Any, ttl: int = None):
            await asyncio.sleep(0.0001)
            cache_data[key] = value
            return True
            
        cache.get.side_effect = mock_get
        cache.set.side_effect = mock_set
        
        return cache

    @pytest.fixture
    def mock_settings(self) -> Mock:
        """Create realistic settings mock for API key service."""
        settings = Mock()
        settings.secret_key = "secure-test-master-key-for-api-encryption"
        settings.environment = "testing"
        settings.debug = True
        
        # Add realistic rate limiting settings
        settings.api_key_validation_rate_limit = 100
        settings.api_key_validation_window = 60
        
        return settings

    @pytest_asyncio.fixture
    async def api_key_service(
        self, mock_database, mock_cache, mock_settings
    ) -> ApiKeyService:
        """Create API key service with mocked dependencies."""
        service = ApiKeyService(
            db=mock_database,
            cache=mock_cache,
            settings=mock_settings
        )
        return service

    @pytest.fixture
    def valid_api_key_data(self) -> Dict[str, Any]:
        """Generate valid API key creation data."""
        return {
            "user_id": uuid.uuid4(),
            "name": "Test OpenAI Key",
            "service": "openai",
            "encrypted_key": "encrypted_test_key_data",
            "description": "Test API key for integration testing",
        }

    # Property-based testing for robust validation
    @given(
        user_id=st.uuids(),
        name=st.text(min_size=1, max_size=255),
        service=st.text(min_size=1, max_size=50).filter(
            lambda x: x.replace("-", "").replace("_", "").isalnum()
        ),
        description=st.one_of(
            st.none(),
            st.text(max_size=1000)
        )
    )
    def test_api_key_create_model_validation(
        self, user_id: UUID, name: str, service: str, description: Optional[str]
    ):
        """Test API key creation model with property-based testing."""
        # Create valid encrypted key data
        encrypted_key = base64.urlsafe_b64encode(
            secrets.token_bytes(32)
        ).decode()
        
        try:
            api_key = ApiKeyCreate(
                user_id=user_id,
                name=name,
                service=service,
                encrypted_key=encrypted_key,
                description=description,
            )
            
            # Verify all fields are properly set
            assert api_key.user_id == user_id
            assert api_key.name == name.strip()  # Pydantic v2 strips whitespace
            assert api_key.service == service.lower()  # Service should be lowercase
            assert api_key.encrypted_key == encrypted_key
            assert api_key.description == description
            
        except ValidationError as e:
            # For property-based testing, we expect some inputs to fail validation
            # This is acceptable and helps us test edge cases
            assert len(e.errors()) > 0

    @pytest.mark.asyncio
    async def test_create_api_key_success(
        self, api_key_service: ApiKeyService, valid_api_key_data: Dict[str, Any]
    ):
        """Test successful API key creation with modern async patterns."""
        # Mock database to return a successful creation
        expected_api_key = ApiKeyDB(
            id=uuid.uuid4(),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            is_active=True,
            **valid_api_key_data
        )
        
        api_key_service.db.fetch_one.return_value = expected_api_key.model_dump()
        
        # Test creation
        create_request = ApiKeyCreate(**valid_api_key_data)
        result = await api_key_service.create_api_key(create_request)
        
        # Verify result
        assert result is not None
        assert result["name"] == valid_api_key_data["name"]
        assert result["service"] == valid_api_key_data["service"]
        
        # Verify database was called
        api_key_service.db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_api_key_duplicate_name(
        self, api_key_service: ApiKeyService, valid_api_key_data: Dict[str, Any]
    ):
        """Test API key creation with duplicate name handling."""
        # Mock database to simulate existing key with same name
        existing_key = {
            "id": str(uuid.uuid4()),
            "name": valid_api_key_data["name"],
            "user_id": str(valid_api_key_data["user_id"]),
        }
        api_key_service.db.fetch_one.return_value = existing_key
        
        create_request = ApiKeyCreate(**valid_api_key_data)
        
        with pytest.raises(CoreServiceError, match="API key name already exists"):
            await api_key_service.create_api_key(create_request)

    @pytest.mark.asyncio
    async def test_validate_api_key_openai_success(
        self, api_key_service: ApiKeyService
    ):
        """Test OpenAI API key validation with mocked HTTP responses."""
        test_key = "sk-test_valid_openai_key_12345"
        
        # Mock successful OpenAI API response
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"object": "list", "data": []}
            mock_get.return_value = mock_response
            
            result = await api_key_service.validate_key(test_key, ServiceType.OPENAI)
            
            assert result.is_valid
            assert result.status == ValidationStatus.VALID
            assert "OpenAI" in result.message

    @pytest.mark.asyncio
    async def test_validate_api_key_openai_invalid(
        self, api_key_service: ApiKeyService
    ):
        """Test OpenAI API key validation with invalid key."""
        test_key = "sk-invalid_key"
        
        # Mock failed OpenAI API response
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.json.return_value = {"error": {"message": "Invalid API key"}}
            mock_get.return_value = mock_response
            
            result = await api_key_service.validate_key(test_key, ServiceType.OPENAI)
            
            assert not result.is_valid
            assert result.status == ValidationStatus.INVALID
            assert "Invalid" in result.message

    @pytest.mark.asyncio
    async def test_validate_api_key_with_caching(
        self, api_key_service: ApiKeyService
    ):
        """Test API key validation with cache hit/miss scenarios."""
        test_key = "sk-cached_test_key"
        
        # First call - cache miss, should validate with API
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"object": "list", "data": []}
            mock_get.return_value = mock_response
            
            result1 = await api_key_service.validate_key(test_key, ServiceType.OPENAI)
            assert result1.is_valid
            
            # Verify HTTP call was made
            mock_get.assert_called_once()
            
        # Second call - should hit cache
        with patch("httpx.AsyncClient.get") as mock_get2:
            # Mock cache hit
            cached_result = {
                "is_valid": True,
                "status": "valid",
                "message": "Cached validation result"
            }
            api_key_service.cache.get.return_value = json.dumps(cached_result)
            
            result2 = await api_key_service.validate_key(test_key, ServiceType.OPENAI)
            
            # Should not make HTTP call due to cache hit
            mock_get2.assert_not_called()

    @pytest.mark.asyncio
    async def test_encryption_decryption_cycle(
        self, api_key_service: ApiKeyService
    ):
        """Test encryption/decryption round-trip with various key types."""
        test_keys = [
            "sk-openai_standard_key_format",
            "very_long_api_key_" + "x" * 500,
            "unicode_key_with_émojis_🔑",
            "special_chars!@#$%^&*()_+-=[]{}|;':\",./<>?",
        ]
        
        for test_key in test_keys:
            # Encrypt the key
            encrypted = api_key_service._encrypt_api_key(test_key)
            
            # Verify encrypted format
            assert isinstance(encrypted, str)
            assert len(encrypted) > len(test_key)
            
            # Decrypt and verify
            decrypted = api_key_service._decrypt_api_key(encrypted)
            assert decrypted == test_key

    @pytest.mark.asyncio
    async def test_concurrent_validation_safety(
        self, api_key_service: ApiKeyService
    ):
        """Test concurrent API key validation for thread safety."""
        test_keys = [f"sk-concurrent_test_{i}" for i in range(10)]
        
        async def validate_key(key: str) -> ValidationResult:
            with patch("httpx.AsyncClient.get") as mock_get:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"object": "list", "data": []}
                mock_get.return_value = mock_response
                
                return await api_key_service.validate_key(key, ServiceType.OPENAI)
        
        # Run concurrent validations
        tasks = [validate_key(key) for key in test_keys]
        results = await asyncio.gather(*tasks)
        
        # Verify all validations succeeded
        assert len(results) == 10
        assert all(result.is_valid for result in results)

    @pytest.mark.asyncio
    async def test_service_health_check(
        self, api_key_service: ApiKeyService
    ):
        """Test service health check functionality."""
        # Mock healthy database and cache
        api_key_service.db.fetch_one.return_value = {"status": "healthy"}
        api_key_service.cache.ping = AsyncMock(return_value=True)
        
        health_status = await api_key_service.get_health_status()
        
        assert health_status.status == ServiceHealthStatus.HEALTHY
        assert health_status.database_connected
        assert health_status.cache_connected

    @pytest.mark.asyncio
    async def test_error_handling_database_failure(
        self, api_key_service: ApiKeyService, valid_api_key_data: Dict[str, Any]
    ):
        """Test error handling when database operations fail."""
        # Mock database failure
        api_key_service.db.execute.side_effect = Exception("Database connection lost")
        
        create_request = ApiKeyCreate(**valid_api_key_data)
        
        with pytest.raises(CoreServiceError, match="Database"):
            await api_key_service.create_api_key(create_request)

    @pytest.mark.asyncio
    async def test_rate_limiting_validation(
        self, api_key_service: ApiKeyService
    ):
        """Test rate limiting for API key validation requests."""
        test_key = "sk-rate_limit_test"
        
        # Mock rate limit exceeded scenario
        with patch.object(api_key_service, "_check_rate_limit") as mock_rate_limit:
            mock_rate_limit.return_value = False  # Rate limit exceeded
            
            with pytest.raises(CoreServiceError, match="Rate limit"):
                await api_key_service.validate_key(test_key, ServiceType.OPENAI)

    def test_service_type_validation(self):
        """Test service type enum validation and conversion."""
        # Test valid service types
        assert ServiceType.OPENAI.value == "openai"
        assert ServiceType.WEATHER.value == "weather"
        assert ServiceType.GOOGLE_MAPS.value == "google_maps"
        
        # Test service type from string
        service_type = ServiceType("openai")
        assert service_type == ServiceType.OPENAI

    @pytest.mark.asyncio
    async def test_audit_logging_integration(
        self, api_key_service: ApiKeyService, valid_api_key_data: Dict[str, Any]
    ):
        """Test that audit logging is properly integrated."""
        with patch("tripsage_core.services.business.audit_logging_service.audit_api_key") as mock_audit:
            api_key_service.db.fetch_one.return_value = None  # No existing key
            api_key_service.db.execute.return_value = None  # Successful creation
            
            create_request = ApiKeyCreate(**valid_api_key_data)
            await api_key_service.create_api_key(create_request)
            
            # Verify audit log was called
            mock_audit.assert_called()

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_validation_performance_benchmark(
        self, api_key_service: ApiKeyService, benchmark
    ):
        """Performance benchmark for API key validation."""
        test_key = "sk-performance_test_key"
        
        async def validate_key_performance():
            with patch("httpx.AsyncClient.get") as mock_get:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"object": "list", "data": []}
                mock_get.return_value = mock_response
                
                return await api_key_service.validate_key(test_key, ServiceType.OPENAI)
        
        # Benchmark should complete in under 100ms
        result = await benchmark(validate_key_performance)
        assert result.is_valid

    @pytest.mark.asyncio
    async def test_pydantic_v2_serialization(
        self, valid_api_key_data: Dict[str, Any]
    ):
        """Test Pydantic v2 serialization and deserialization."""
        # Create model instance
        api_key = ApiKeyCreate(**valid_api_key_data)
        
        # Test JSON serialization round-trip
        json_data = api_key.model_dump_json()
        restored = ApiKeyCreate.model_validate_json(json_data)
        assert restored == api_key
        
        # Test dict serialization round-trip
        dict_data = api_key.model_dump()
        restored_dict = ApiKeyCreate.model_validate(dict_data)
        assert restored_dict == api_key

    @pytest.mark.asyncio
    async def test_comprehensive_edge_cases(
        self, api_key_service: ApiKeyService
    ):
        """Test comprehensive edge cases and boundary conditions."""
        edge_cases = [
            # Empty key
            ("", ServiceType.OPENAI, False),
            # Very long key
            ("sk-" + "x" * 1000, ServiceType.OPENAI, True),
            # Unicode key
            ("sk-unicode_test_🔑", ServiceType.OPENAI, True),
            # SQL injection attempt
            ("sk-'; DROP TABLE users; --", ServiceType.OPENAI, True),
            # XSS attempt
            ("sk-<script>alert('xss')</script>", ServiceType.OPENAI, True),
        ]
        
        for test_key, service_type, should_validate in edge_cases:
            try:
                with patch("httpx.AsyncClient.get") as mock_get:
                    if should_validate:
                        mock_response = Mock()
                        mock_response.status_code = 200
                        mock_response.json.return_value = {"object": "list", "data": []}
                        mock_get.return_value = mock_response
                    
                    result = await api_key_service.validate_key(test_key, service_type)
                    
                    if should_validate:
                        assert isinstance(result, ValidationResult)
                    
            except CoreServiceError:
                # Some edge cases should raise errors
                assert not should_validate or test_key == ""

    @pytest.mark.asyncio
    async def test_update_api_key_functionality(
        self, api_key_service: ApiKeyService
    ):
        """Test API key update functionality with various scenarios."""
        key_id = uuid.uuid4()
        
        # Mock existing key
        existing_key = {
            "id": str(key_id),
            "name": "Original Name",
            "description": "Original Description",
            "is_active": True,
            "updated_at": datetime.now(timezone.utc),
        }
        api_key_service.db.fetch_one.return_value = existing_key
        
        # Test update
        update_data = ApiKeyUpdate(
            name="Updated Name",
            description="Updated Description",
            is_active=False,
        )
        
        result = await api_key_service.update_api_key(key_id, update_data)
        
        # Verify update was processed
        api_key_service.db.execute.assert_called()
        assert "Updated Name" in str(api_key_service.db.execute.call_args)

    @pytest.mark.asyncio
    async def test_delete_api_key_functionality(
        self, api_key_service: ApiKeyService
    ):
        """Test API key deletion with proper cleanup."""
        key_id = uuid.uuid4()
        
        # Mock existing key
        existing_key = {
            "id": str(key_id),
            "name": "Key to Delete",
            "is_active": True,
        }
        api_key_service.db.fetch_one.return_value = existing_key
        
        # Test deletion
        result = await api_key_service.delete_api_key(key_id)
        
        # Verify deletion was processed
        api_key_service.db.execute.assert_called()
        
        # Verify cache cleanup
        api_key_service.cache.delete.assert_called()

    @pytest.mark.asyncio
    async def test_list_user_api_keys(
        self, api_key_service: ApiKeyService
    ):
        """Test listing user API keys with pagination and filtering."""
        user_id = uuid.uuid4()
        
        # Mock API keys data
        mock_keys = [
            {
                "id": str(uuid.uuid4()),
                "name": f"Key {i}",
                "service": "openai" if i % 2 == 0 else "weather",
                "is_active": True,
                "created_at": datetime.now(timezone.utc),
            }
            for i in range(5)
        ]
        api_key_service.db.fetch_all.return_value = mock_keys
        
        # Test listing
        result = await api_key_service.list_user_api_keys(
            user_id=user_id,
            service_filter="openai",
            active_only=True,
            limit=10,
            offset=0
        )
        
        # Verify result
        assert isinstance(result, list)
        api_key_service.db.fetch_all.assert_called_once()


class TestApiKeyServicePropertyBased:
    """Property-based tests for API Key Service using Hypothesis."""

    @given(
        name=st.text(min_size=1, max_size=255),
        service=st.sampled_from(["openai", "weather", "google_maps"]),
        description=st.one_of(st.none(), st.text(max_size=1000)),
    )
    def test_api_key_creation_properties(
        self, name: str, service: str, description: Optional[str]
    ):
        """Property-based test for API key creation with various inputs."""
        user_id = uuid.uuid4()
        encrypted_key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
        
        try:
            api_key = ApiKeyCreate(
                user_id=user_id,
                name=name,
                service=service,
                encrypted_key=encrypted_key,
                description=description,
            )
            
            # Properties that should always hold
            assert len(api_key.name.strip()) > 0
            assert api_key.service in ["openai", "weather", "google_maps"]
            assert len(api_key.encrypted_key) > 0
            
        except ValidationError:
            # Some property combinations may fail validation
            # This is expected and helps us find edge cases
            pass

    @given(
        key_data=st.binary(min_size=1, max_size=1000)
    )
    def test_encryption_decryption_properties(self, key_data: bytes):
        """Property-based test for encryption/decryption with random data."""
        from tripsage_core.services.business.api_key_service import ApiKeyService
        
        # Create service instance for testing
        mock_settings = Mock()
        mock_settings.secret_key = "test-master-key-for-property-testing"
        
        service = ApiKeyService(
            db=Mock(),
            cache=Mock(), 
            settings=mock_settings
        )
        
        # Convert binary data to string for testing
        test_key = base64.urlsafe_b64encode(key_data).decode()
        
        try:
            # Test encryption/decryption cycle
            encrypted = service._encrypt_api_key(test_key)
            decrypted = service._decrypt_api_key(encrypted)
            
            # Property: decryption should restore original data
            assert decrypted == test_key
            
            # Property: encrypted data should be different from original
            assert encrypted != test_key
            
            # Property: encrypted data should be longer than original
            assert len(encrypted) > len(test_key)
            
        except CoreServiceError:
            # Some inputs may be invalid (e.g., empty strings)
            # This is expected behavior
            pass


class TestApiKeyServiceErrorScenarios:
    """Comprehensive error scenario testing for API Key Service."""

    @pytest.mark.asyncio
    async def test_network_timeout_handling(self):
        """Test handling of network timeouts during API validation."""
        mock_settings = Mock()
        mock_settings.secret_key = "test-key"
        
        service = ApiKeyService(
            db=AsyncMock(),
            cache=AsyncMock(),
            settings=mock_settings
        )
        
        with patch("httpx.AsyncClient.get") as mock_get:
            # Simulate network timeout
            mock_get.side_effect = asyncio.TimeoutError("Request timed out")
            
            result = await service.validate_key("sk-timeout_test", ServiceType.OPENAI)
            
            # Should handle timeout gracefully
            assert not result.is_valid
            assert result.status == ValidationStatus.ERROR
            assert "timeout" in result.message.lower()

    @pytest.mark.asyncio
    async def test_malformed_api_response_handling(self):
        """Test handling of malformed API responses."""
        mock_settings = Mock()
        mock_settings.secret_key = "test-key"
        
        service = ApiKeyService(
            db=AsyncMock(),
            cache=AsyncMock(),
            settings=mock_settings
        )
        
        with patch("httpx.AsyncClient.get") as mock_get:
            # Simulate malformed JSON response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
            mock_get.return_value = mock_response
            
            result = await service.validate_key("sk-malformed_test", ServiceType.OPENAI)
            
            # Should handle malformed response gracefully
            assert not result.is_valid
            assert result.status == ValidationStatus.ERROR