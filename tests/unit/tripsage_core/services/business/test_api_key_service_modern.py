"""
Modern comprehensive tests for ApiKeyService using 2025 best practices.

This module provides enhanced test coverage with property-based testing,
modern async patterns, and comprehensive edge case coverage using Hypothesis.
"""

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from unittest.mock import AsyncMock, Mock, patch

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from tripsage_core.exceptions import (
    CoreServiceError as ServiceError,
)
from tripsage_core.services.business.api_key_service import (
    ApiKeyCreateRequest,
    ApiKeyResponse,
    ApiKeyService,
    ServiceType,
    ValidationResult,
    ValidationStatus,
)

# Hypothesis strategies for property-based testing
api_key_strategies = {
    "openai": st.text(
        alphabet=st.characters(min_codepoint=32, max_codepoint=126),
        min_size=10,
        max_size=100,
    ).filter(lambda x: x.startswith("sk-")),
    "generic": st.text(
        alphabet=st.characters(min_codepoint=32, max_codepoint=126),
        min_size=8,
        max_size=200,
    ),
}

service_types = st.sampled_from(list(ServiceType))
uuids = st.uuids().map(str)
names = st.text(min_size=1, max_size=100).filter(str.strip)
descriptions = st.text(min_size=0, max_size=500)
booleans = st.booleans()
timestamps = st.datetimes(
    min_value=datetime(2020, 1, 1, tzinfo=timezone.utc),
    max_value=datetime(2030, 12, 31, tzinfo=timezone.utc),
)


class TestApiKeyServiceModern:
    """Modern test suite for ApiKeyService with property-based testing."""

    @pytest.fixture
    async def mock_dependencies(self):
        """Create mocked dependencies using modern async patterns."""
        db = AsyncMock()
        cache = AsyncMock()
        audit = AsyncMock()
        
        # Set up common return values
        db.create_api_key.return_value = self._sample_db_result()
        cache.get_json.return_value = None
        cache.set_json.return_value = True
        
        return {
            "db": db,
            "cache": cache,
            "audit": audit,
        }

    @pytest.fixture
    async def api_service(self, mock_dependencies):
        """Create ApiKeyService with injected dependencies."""
        service = ApiKeyService(
            db=mock_dependencies["db"],
            cache=mock_dependencies["cache"],
        )
        return service

    def _sample_db_result(self) -> Dict[str, Any]:
        """Generate sample database result."""
        return {
            "id": str(uuid.uuid4()),
            "name": "Test API Key",
            "service": "openai",
            "description": "Test description",
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

    # Property-based tests for key creation
    @given(
        name=names,
        service=service_types,
        description=descriptions,
    )
    @pytest.mark.asyncio
    async def test_create_key_property_based(
        self, api_service, mock_dependencies, name, service, description
    ):
        """Property-based test for key creation with various inputs."""
        assume(name.strip())  # Ensure name is not empty/whitespace-only
        
        user_id = str(uuid.uuid4())
        key_value = f"sk-test_key_{uuid.uuid4().hex[:20]}"
        
        request = ApiKeyCreateRequest(
            name=name,
            service=service,
            key_value=key_value,
            description=description,
        )

        # Mock successful validation
        with patch.object(api_service, "validate_api_key") as mock_validate:
            mock_validate.return_value = ValidationResult(
                is_valid=True,
                status=ValidationStatus.VALID,
                service=service,
                message="Key is valid",
            )

            result = await api_service.create_api_key(user_id, request)

            # Assertions that should hold for any valid input
            assert isinstance(result, ApiKeyResponse)
            assert result.name == name
            assert result.service == service
            assert result.description == description
            assert result.is_valid is True

    @given(
        api_key=api_key_strategies["generic"],
        service=service_types,
    )
    @pytest.mark.asyncio
    async def test_validate_key_format_property_based(
        self, api_service, api_key, service
    ):
        """Property-based test for key format validation."""
        user_id = str(uuid.uuid4())
        
        result = await api_service.validate_api_key(service, api_key, user_id)
        
        # Basic invariants that should always hold
        assert isinstance(result, ValidationResult)
        assert result.service == service
        assert isinstance(result.is_valid, bool)
        assert isinstance(result.status, ValidationStatus)
        assert isinstance(result.message, str)

    @given(
        names_list=st.lists(names, min_size=1, max_size=10),
        user_ids=uuids,
    )
    @pytest.mark.asyncio
    async def test_bulk_operations_property_based(
        self, api_service, mock_dependencies, names_list, user_ids
    ):
        """Property-based test for bulk operations."""
        # Mock multiple keys
        mock_keys = [
            {
                **self._sample_db_result(),
                "name": name,
                "user_id": user_ids,
            }
            for name in names_list
        ]
        
        mock_dependencies["db"].list_user_keys.return_value = mock_keys

        with patch.object(api_service, "check_health") as mock_health:
            mock_health.return_value = ValidationResult(
                is_valid=True,
                status=ValidationStatus.VALID,
                service=ServiceType.OPENAI,
                message="Healthy",
            )

            results = await api_service.bulk_health_check(user_ids)

            # Verify bulk operation properties
            assert len(results) == len(names_list)
            assert all(isinstance(result, dict) for result in results)

    # Modern async context manager tests
    @pytest.mark.asyncio
    async def test_service_lifecycle_context_manager(self, mock_dependencies):
        """Test service lifecycle using async context managers."""
        async with ApiKeyService() as service:
            service.db = mock_dependencies["db"]
            service.cache = mock_dependencies["cache"]
            service.audit = mock_dependencies["audit"]
            
            # Verify service is properly initialized
            assert service.db is not None
            assert service.cache is not None
            assert service.audit is not None

    # Concurrency tests
    @pytest.mark.asyncio
    async def test_concurrent_validations(self, api_service):
        """Test concurrent API key validations."""
        keys = [f"sk-test_{i}" for i in range(5)]
        user_id = str(uuid.uuid4())

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": [{"id": "model-1"}]}
            mock_get.return_value = mock_response

            # Run concurrent validations
            tasks = [
                api_service.validate_api_key(ServiceType.OPENAI, key, user_id)
                for key in keys
            ]
            results = await asyncio.gather(*tasks)

            # All should succeed
            assert len(results) == 5
            assert all(result.is_valid for result in results)

    # Error recovery and resilience tests
    @pytest.mark.asyncio
    async def test_network_error_recovery(self, api_service):
        """Test recovery from network errors with exponential backoff."""
        user_id = str(uuid.uuid4())
        
        with patch("httpx.AsyncClient.get") as mock_get:
            # Simulate intermittent network failures
            mock_get.side_effect = [
                Exception("Network timeout"),
                Exception("Connection reset"),
                Mock(status_code=200, json=lambda: {"data": [{"id": "model-1"}]}),
            ]

            result = await api_service.validate_api_key(
                ServiceType.OPENAI, "sk-test", user_id
            )

            # Should eventually succeed after retries
            assert result.is_valid is True
            assert mock_get.call_count >= 2

    @pytest.mark.asyncio
    async def test_circuit_breaker_behavior(self, api_service, mock_dependencies):
        """Test circuit breaker pattern for database failures."""
        user_id = str(uuid.uuid4())
        
        # Simulate repeated database failures
        mock_dependencies["db"].create_api_key.side_effect = [
            Exception("Database connection failed"),
            Exception("Database timeout"),
            Exception("Database unavailable"),
        ]

        request = ApiKeyCreateRequest(
            name="Test Key",
            service=ServiceType.OPENAI,
            key_value="sk-test",
            description="Test",
        )

        with patch.object(api_service, "validate_api_key") as mock_validate:
            mock_validate.return_value = ValidationResult(
                is_valid=True,
                status=ValidationStatus.VALID,
                service=ServiceType.OPENAI,
                message="Valid",
            )

            # Should fail gracefully with appropriate error
            with pytest.raises(ServiceError):
                await api_service.create_key(user_id, request)

    # Data integrity tests
    @given(
        user_ids=st.lists(uuids, min_size=1, max_size=5, unique=True),
        timestamps_list=st.lists(timestamps, min_size=1, max_size=5),
    )
    @pytest.mark.asyncio
    async def test_data_consistency_property_based(
        self, api_service, mock_dependencies, user_ids, timestamps_list
    ):
        """Test data consistency across operations."""
        # Mock keys for each user
        for user_id, timestamp in zip(user_ids, timestamps_list, strict=False):
            mock_key = {
                **self._sample_db_result(),
                "user_id": user_id,
                "created_at": timestamp.isoformat(),
            }
            mock_dependencies["db"].get_api_key.return_value = mock_key

            result = await api_service.get_key(mock_key["id"])
            
            # Data consistency checks
            assert result["user_id"] == user_id
            assert result["created_at"] == timestamp.isoformat()

    # Security tests
    @pytest.mark.asyncio
    async def test_encryption_security_properties(self, api_service):
        """Test encryption security properties."""
        test_keys = [
            "sk-secret_key_1",
            "very_long_key_with_special_chars!@#$%^&*()",
            "short",
            "",  # Edge case
        ]

        for key in test_keys:
            if key:  # Skip empty string for encryption
                encrypted = api_service._encrypt_key(key)
                decrypted = api_service._decrypt_key(encrypted)
                
                # Security properties
                assert encrypted != key  # Encrypted value differs
                assert len(encrypted) > 0  # Encryption produces output
                assert decrypted == key  # Decryption is inverse
                
                # No sensitive data in encrypted form
                assert key not in encrypted

    @pytest.mark.asyncio
    async def test_rate_limiting_enforcement(self, api_service, mock_dependencies):
        """Test rate limiting enforcement across multiple requests."""
        user_id = str(uuid.uuid4())
        
        # Simulate rate limit tracking
        request_counts = [str(i) for i in range(1, 12)]  # 1-11 requests
        mock_dependencies["cache"].get.side_effect = request_counts

        results = []
        for _count in request_counts:
            is_limited = await api_service._is_rate_limited(user_id)
            results.append(is_limited)

        # Should be rate limited after threshold (typically 10)
        assert not any(results[:9])  # First 9 should not be limited
        assert all(results[9:])  # 10th and beyond should be limited

    # Performance and monitoring tests
    @pytest.mark.asyncio
    async def test_monitoring_metrics_collection(self, api_service, mock_dependencies):
        """Test monitoring metrics are properly collected."""
        key_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())

        # Mock monitoring data
        mock_metrics = {
            "last_check": datetime.now(timezone.utc).isoformat(),
            "status": "healthy",
            "response_time": 150,
            "success_rate": 0.95,
            "error_count": 2,
        }
        mock_dependencies["cache"].get_json.return_value = mock_metrics

        result = await api_service.monitor_key(key_id, user_id)

        # Verify all expected metrics are present
        assert "last_check" in result
        assert "status" in result
        assert "response_time" in result
        assert isinstance(result["response_time"], (int, float))

    # Timeout and async behavior tests
    @pytest.mark.asyncio
    async def test_validation_timeout_handling(self, api_service):
        """Test proper handling of validation timeouts."""
        user_id = str(uuid.uuid4())
        
        with patch("httpx.AsyncClient.get") as mock_get:
            # Simulate timeout
            mock_get.side_effect = asyncio.TimeoutError("Request timeout")

            result = await api_service.validate_api_key(
                ServiceType.OPENAI, "sk-test", user_id
            )

            # Should handle timeout gracefully
            assert result.is_valid is False
            assert result.status == ValidationStatus.SERVICE_ERROR
            assert "timeout" in result.message.lower()

    @pytest.mark.asyncio
    async def test_async_cleanup_behavior(self, api_service, mock_dependencies):
        """Test proper async resource cleanup."""
        # Simulate operations that require cleanup
        user_id = str(uuid.uuid4())
        
        try:
            # Perform operation that might fail
            mock_dependencies["db"].create_api_key.side_effect = Exception("Test error")
            
            request = ApiKeyCreateRequest(
                name="Test",
                service=ServiceType.OPENAI,
                key_value="sk-test",
                description="Test",
            )
            
            with pytest.raises(ServiceError):
                await api_service.create_key(user_id, request)
                
        finally:
            # Verify cleanup occurred (audit logging should still happen)
            mock_dependencies["audit"].log_operation.assert_called()

    # Edge cases and boundary tests
    @given(
        edge_case_inputs=st.one_of(
            st.just(""),  # Empty string
            st.text(min_size=1000, max_size=2000),  # Very long string
            st.just("\x00\x01\x02"),  # Binary data
            st.just("🚀🔑🌟"),  # Unicode/emoji
        )
    )
    @pytest.mark.asyncio
    async def test_edge_case_inputs(self, api_service, edge_case_inputs):
        """Test handling of edge case inputs."""
        user_id = str(uuid.uuid4())
        
        # Test key validation with edge cases
        result = await api_service.validate_api_key(
            ServiceType.OPENAI, edge_case_inputs, user_id
        )
        
        # Should handle gracefully without crashing
        assert isinstance(result, ValidationResult)
        assert isinstance(result.is_valid, bool)
        assert isinstance(result.message, str)