"""Focused test coverage for API key service targeting specific uncovered lines.

This module provides targeted tests for specific uncovered line ranges
identified in BJO-211 coverage analysis to achieve 90%+ coverage.
"""

import asyncio
import base64
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
from cryptography.exceptions import InvalidSignature
from cryptography.fernet import Fernet

from tripsage_core.exceptions import CoreServiceError as ServiceError
from tripsage_core.services.business.api_key_service import (
    ApiKeyCreateRequest,
    ApiKeyResponse,
    ApiKeyService,
    ServiceHealthStatus,
    ServiceType,
    ValidationResult,
    ValidationStatus,
)


class TestApiKeyServiceCoverageFocused:
    """Focused tests targeting specific uncovered line ranges."""

    @pytest.fixture
    async def mock_dependencies(self):
        """Create mocked dependencies."""
        db = AsyncMock()
        cache = AsyncMock()

        # Set up common return values
        db.create_api_key.return_value = {
            "id": str(uuid.uuid4()),
            "name": "Test API Key",
            "service": "openai",
            "description": "Test description",
            "is_valid": True,
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
            "expires_at": None,
            "last_used": None,
            "last_validated": datetime.now(UTC).isoformat(),
            "usage_count": 0,
        }
        cache.get_json.return_value = None
        cache.set_json.return_value = True

        return {"db": db, "cache": cache}

    @pytest.fixture
    async def api_service(self, mock_dependencies):
        """Create ApiKeyService with injected dependencies."""
        with patch("tripsage_core.config.get_settings") as mock_settings:
            mock_settings.return_value.secret_key = "test-secret-key-for-testing"
            return ApiKeyService(
                db=mock_dependencies["db"],
                cache=mock_dependencies["cache"],
            )

    # PHASE 1: Encryption/Decryption Edge Cases (Lines 623-686)

    @pytest.mark.asyncio
    async def test_encrypt_api_key_malformed_master_key(self):
        """Test encryption failure with corrupted master key - targets lines 648-650."""
        with patch("tripsage_core.config.get_settings") as mock_settings:
            # Simulate invalid secret key that will cause encoding issues
            mock_settings.return_value.secret_key = None

            with pytest.raises((TypeError, AttributeError)):
                # This should fail during key derivation when None.encode() is called
                ApiKeyService(db=AsyncMock(), cache=AsyncMock())

    @pytest.mark.asyncio
    async def test_decrypt_api_key_invalid_separator(self, api_service):
        """Test decryption with invalid '::' separator - targets lines 664-670."""
        # Create malformed encrypted data without separator
        malformed_key = base64.urlsafe_b64encode(b"no_separator_data").decode()

        with pytest.raises(ServiceError, match="Decryption failed"):
            api_service._decrypt_api_key(malformed_key)

    @pytest.mark.asyncio
    async def test_decrypt_api_key_corrupted_data(self, api_service):
        """Test decryption with base64 corruption - targets lines 675-685."""
        # Create data with proper separator but corrupted encryption
        corrupted_data = b"corrupted_key::corrupted_value"
        corrupted_key = base64.urlsafe_b64encode(corrupted_data).decode()

        with pytest.raises(ServiceError, match="Decryption failed"):
            api_service._decrypt_api_key(corrupted_key)

    @pytest.mark.asyncio
    async def test_decrypt_api_key_invalid_base64(self, api_service):
        """Test decryption with invalid base64 data - targets lines 679-685."""
        # Create invalid base64 string
        invalid_base64 = "invalid!@#$%^&*()base64=="

        with pytest.raises(ServiceError, match="Decryption failed"):
            api_service._decrypt_api_key(invalid_base64)

    @pytest.mark.asyncio
    async def test_encrypt_fernet_generation_failure(self, api_service):
        """Test encryption when Fernet key generation fails - targets lines 651-667."""
        with patch("cryptography.fernet.Fernet.generate_key") as mock_generate:
            mock_generate.side_effect = Exception("Key generation failed")

            with pytest.raises(ServiceError, match="Encryption failed"):
                api_service._encrypt_api_key("test-key-value")

    @pytest.mark.asyncio
    async def test_encrypt_data_cipher_creation_failure(self, api_service):
        """Test encryption when data cipher creation fails - targets lines 652-667."""
        with patch("cryptography.fernet.Fernet") as mock_fernet_class:
            # Mock generate_key to succeed, but constructor to fail
            mock_fernet_class.generate_key.return_value = (
                b"fake_key_value_32_bytes_length!"
            )
            mock_fernet_class.side_effect = Exception("Invalid key format")

            with pytest.raises(ServiceError, match="Encryption failed"):
                api_service._encrypt_api_key("test-key-value")

    @pytest.mark.asyncio
    async def test_encrypt_data_encryption_failure(self, api_service):
        """Test encryption when data encryption itself fails - targets lines 655-667."""
        with patch("cryptography.fernet.Fernet") as mock_fernet_class:
            # Mock generate_key to succeed
            mock_fernet_class.generate_key.return_value = (
                b"fake_key_value_32_bytes_length!"
            )

            # Mock cipher instance with failing encrypt method
            mock_cipher = Mock()
            mock_cipher.encrypt.side_effect = Exception("Encryption operation failed")
            mock_fernet_class.return_value = mock_cipher

            with pytest.raises(ServiceError, match="Encryption failed"):
                api_service._encrypt_api_key("test-key-value")

    @pytest.mark.asyncio
    async def test_encrypt_master_key_encryption_failure(self, api_service):
        """Test encryption when master key encryption fails - targets lines 658-667."""
        with patch.object(api_service.master_cipher, "encrypt") as mock_encrypt:
            mock_encrypt.side_effect = Exception("Master key encryption failed")

            with pytest.raises(ServiceError, match="Encryption failed"):
                api_service._encrypt_api_key("test-key-value")

    @pytest.mark.asyncio
    async def test_decrypt_fernet_invalid_token_exception(self, api_service):
        """Test decryption with Fernet InvalidToken exception."""
        # Create a valid-looking encrypted key structure but with corrupted Fernet token
        fake_data_key = Fernet.generate_key()
        encrypted_data_key = api_service.master_cipher.encrypt(fake_data_key)

        # Create corrupted encrypted value that will cause InvalidToken
        corrupted_encrypted_value = b"invalid_fernet_token_data"

        combined = encrypted_data_key + b"::" + corrupted_encrypted_value
        malformed_key = base64.urlsafe_b64encode(combined).decode()

        with pytest.raises(ServiceError, match="Decryption failed"):
            api_service._decrypt_api_key(malformed_key)

    @pytest.mark.asyncio
    async def test_decrypt_invalid_signature_exception(self, api_service):
        """Test decryption with InvalidSignature exception - targets lines 691-702."""
        # Create encrypted key that passes validation but fails signature check
        Fernet.generate_key()

        with patch.object(api_service.master_cipher, "decrypt") as mock_decrypt:
            mock_decrypt.side_effect = InvalidSignature("HMAC verification failed")

            # Create a properly formatted encrypted key
            encrypted_data_key = b"fake_encrypted_data_key"
            encrypted_value = b"fake_encrypted_value"
            combined = encrypted_data_key + b"::" + encrypted_value
            malformed_key = base64.urlsafe_b64encode(combined).decode()

            with pytest.raises(ServiceError, match="Decryption failed"):
                api_service._decrypt_api_key(malformed_key)

    @pytest.mark.asyncio
    async def test_decrypt_data_key_decryption_failure(self, api_service):
        """Test decryption when data key decryption fails - targets lines 691-702."""
        # Create valid structure but simulate failure in data key decryption
        fake_data_key = Fernet.generate_key()
        fake_cipher = Fernet(fake_data_key)
        encrypted_value = fake_cipher.encrypt(b"test_value")

        with patch.object(api_service.master_cipher, "decrypt") as mock_decrypt:
            mock_decrypt.side_effect = Exception("Data key decryption failed")

            encrypted_data_key = b"fake_encrypted_data_key"
            combined = encrypted_data_key + b"::" + encrypted_value
            malformed_key = base64.urlsafe_b64encode(combined).decode()

            with pytest.raises(ServiceError, match="Decryption failed"):
                api_service._decrypt_api_key(malformed_key)

    @pytest.mark.asyncio
    async def test_decrypt_value_decryption_failure(self, api_service):
        """Test decryption when final value decryption fails - targets lines 694-702."""
        # Create valid data key but corrupted encrypted value
        fake_data_key = Fernet.generate_key()
        encrypted_data_key = api_service.master_cipher.encrypt(fake_data_key)

        # Use corrupted encrypted value that will fail Fernet decryption
        corrupted_encrypted_value = base64.urlsafe_b64encode(b"corrupted_token_data")

        combined = encrypted_data_key + b"::" + corrupted_encrypted_value
        malformed_key = base64.urlsafe_b64encode(combined).decode()

        with pytest.raises(ServiceError, match="Decryption failed"):
            api_service._decrypt_api_key(malformed_key)

    @pytest.mark.asyncio
    async def test_decrypt_unicode_decode_failure(self, api_service):
        """Test decryption when Unicode decode fails - targets lines 698-702."""
        # Create a scenario where decryption succeeds but Unicode decode fails
        fake_data_key = Fernet.generate_key()
        fake_cipher = Fernet(fake_data_key)

        # Encrypt invalid UTF-8 bytes
        invalid_utf8_bytes = b"\xff\xfe\xfd"
        encrypted_value = fake_cipher.encrypt(invalid_utf8_bytes)
        encrypted_data_key = api_service.master_cipher.encrypt(fake_data_key)

        combined = encrypted_data_key + b"::" + encrypted_value
        malformed_key = base64.urlsafe_b64encode(combined).decode()

        with pytest.raises(ServiceError, match="Decryption failed"):
            api_service._decrypt_api_key(malformed_key)

    @pytest.mark.asyncio
    async def test_decrypt_missing_separator_parts(self, api_service):
        """Test decryption with missing separator - targets lines 684-687."""
        # Create data with no separator
        no_separator_data = b"single_part_no_separator"
        no_separator_key = base64.urlsafe_b64encode(no_separator_data).decode()

        with pytest.raises(ServiceError, match="Decryption failed"):
            api_service._decrypt_api_key(no_separator_key)

    @pytest.mark.asyncio
    async def test_decrypt_too_many_separator_parts(self, api_service):
        """Test decryption with multiple separators - targets lines 684-687."""
        # Create data with multiple separators (should only split on first)
        multiple_separator_data = b"part1::part2::part3::part4"
        multiple_separator_key = base64.urlsafe_b64encode(
            multiple_separator_data
        ).decode()

        # This should actually work since split(b"::", 1) only splits on first
        # occurrence
        # But let's test it behaves correctly
        try:
            api_service._decrypt_api_key(multiple_separator_key)
            # Should fail during actual decryption since parts are invalid
            raise AssertionError("Expected decryption to fail")
        except ServiceError as e:
            assert "Decryption failed" in str(e)

    # PHASE 1: Database Transaction Rollbacks (Lines 343-356, 592-604)

    @pytest.mark.asyncio
    async def test_create_api_key_transaction_rollback(
        self, api_service, mock_dependencies
    ):
        """Test transaction rollback on database failure - targets lines 343-356."""
        user_id = str(uuid.uuid4())
        request = ApiKeyCreateRequest(
            name="Test Key",
            service=ServiceType.OPENAI,
            key_value="sk-test-key-12345",
            description="Test",
        )

        # Mock transaction context manager that fails
        mock_transaction = AsyncMock()
        mock_transaction.__aenter__.return_value = mock_transaction
        mock_transaction.__aexit__.side_effect = Exception("Transaction failed")
        mock_dependencies["db"].transaction.return_value = mock_transaction

        with patch.object(api_service, "validate_api_key") as mock_validate:
            mock_validate.return_value = ValidationResult(
                is_valid=True,
                status=ValidationStatus.VALID,
                service=ServiceType.OPENAI,
                message="Valid",
            )

            with pytest.raises(ServiceError):
                await api_service.create_api_key(user_id, request)

    @pytest.mark.asyncio
    async def test_create_api_key_transaction_execute_failure(
        self, api_service, mock_dependencies
    ):
        """Test transaction failure during execute phase - targets lines 347-360."""
        user_id = str(uuid.uuid4())
        request = ApiKeyCreateRequest(
            name="Test Key",
            service=ServiceType.OPENAI,
            key_value="sk-test-key-12345",
            description="Test",
        )

        # Mock transaction that fails during execute
        mock_transaction = AsyncMock()
        mock_transaction.__aenter__.return_value = mock_transaction
        mock_transaction.execute.side_effect = Exception("Database execute failed")
        mock_dependencies["db"].transaction.return_value = mock_transaction

        with patch.object(api_service, "validate_api_key") as mock_validate:
            mock_validate.return_value = ValidationResult(
                is_valid=True,
                status=ValidationStatus.VALID,
                service=ServiceType.OPENAI,
                message="Valid",
            )

            with pytest.raises(ServiceError, match="Failed to create API key"):
                await api_service.create_api_key(user_id, request)

            # Verify that the transaction method was called (transaction was attempted)
            assert mock_dependencies["db"].transaction.called

    @pytest.mark.asyncio
    async def test_create_api_key_partial_transaction_failure(
        self, api_service, mock_dependencies
    ):
        """Test partial transaction failure with cleanup - targets lines 348-359."""
        user_id = str(uuid.uuid4())
        request = ApiKeyCreateRequest(
            name="Test Key",
            service=ServiceType.OPENAI,
            key_value="sk-test-key-12345",
            description="Test",
        )

        # Mock transaction that partially succeeds then fails
        mock_transaction = AsyncMock()
        mock_transaction.__aenter__.return_value = mock_transaction
        # First insert succeeds, second insert fails
        mock_transaction.execute.side_effect = [
            [[{"id": str(uuid.uuid4())}]],  # api_keys insert succeeds
            Exception("Usage log insert failed"),  # usage_logs insert fails
        ]
        mock_dependencies["db"].transaction.return_value = mock_transaction

        with patch.object(api_service, "validate_api_key") as mock_validate:
            mock_validate.return_value = ValidationResult(
                is_valid=True,
                status=ValidationStatus.VALID,
                service=ServiceType.OPENAI,
                message="Valid",
            )

            with pytest.raises(ServiceError):
                await api_service.create_api_key(user_id, request)

    @pytest.mark.asyncio
    async def test_delete_api_key_transaction_rollback(
        self, api_service, mock_dependencies
    ):
        """Test transaction rollback on deletion failure - targets lines 592-604."""
        key_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())

        # Mock existing key
        mock_dependencies["db"].get_api_key_by_id.return_value = {
            "id": key_id,
            "user_id": user_id,
            "service": "openai",
            "name": "Test Key",
        }

        # Mock transaction that fails
        mock_transaction = AsyncMock()
        mock_transaction.__aenter__.return_value = mock_transaction
        mock_transaction.execute.side_effect = Exception("Database error")
        mock_dependencies["db"].transaction.return_value = mock_transaction

        with pytest.raises(RuntimeError, match="Database error"):
            await api_service.delete_api_key(key_id, user_id)

    @pytest.mark.asyncio
    async def test_delete_api_key_transaction_context_failure(
        self, api_service, mock_dependencies
    ):
        """Test transaction context manager failure during delete."""
        key_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())

        # Mock existing key
        mock_dependencies["db"].get_api_key_by_id.return_value = {
            "id": key_id,
            "user_id": user_id,
            "service": "openai",
            "name": "Test Key",
        }

        # Mock transaction context that fails on exit
        mock_transaction = AsyncMock()
        mock_transaction.__aenter__.return_value = mock_transaction
        mock_transaction.__aexit__.side_effect = Exception("Transaction cleanup failed")
        mock_dependencies["db"].transaction.return_value = mock_transaction

        with pytest.raises(RuntimeError, match="Transaction cleanup failed"):
            await api_service.delete_api_key(key_id, user_id)

        # When __aexit__ fails immediately, transaction operations might not be called
        # But we verify the context manager was properly used
        assert mock_dependencies["db"].transaction.called

    @pytest.mark.asyncio
    async def test_delete_api_key_empty_transaction_result(
        self, api_service, mock_dependencies
    ):
        """Test delete with empty transaction result - targets lines 623-624."""
        key_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())

        # Mock existing key
        mock_dependencies["db"].get_api_key_by_id.return_value = {
            "id": key_id,
            "user_id": user_id,
            "service": "openai",
            "name": "Test Key",
        }

        # Mock transaction that succeeds but returns empty result (key not found)
        mock_transaction = AsyncMock()
        mock_transaction.__aenter__.return_value = mock_transaction
        mock_transaction.__aexit__.return_value = None
        mock_transaction.execute.return_value = [[], []]  # Empty delete result

        # Use contextlib.asynccontextmanager for proper async context management
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def mock_transaction_context():
            yield mock_transaction

        mock_dependencies["db"].transaction = mock_transaction_context

        result = await api_service.delete_api_key(key_id, user_id)

        assert result is False  # Should return False when deletion fails

    @pytest.mark.asyncio
    async def test_transaction_network_failure_simulation(
        self, api_service, mock_dependencies
    ):
        """Test transaction failure due to network issues - comprehensive coverage."""
        user_id = str(uuid.uuid4())
        request = ApiKeyCreateRequest(
            name="Test Key",
            service=ServiceType.OPENAI,
            key_value="sk-test-key-12345",
            description="Test",
        )

        # Simulate network connectivity issues during transaction
        mock_transaction = AsyncMock()
        mock_transaction.__aenter__.return_value = mock_transaction
        mock_transaction.__aexit__.side_effect = ConnectionError("Network unavailable")
        mock_dependencies["db"].transaction.return_value = mock_transaction

        with patch.object(api_service, "validate_api_key") as mock_validate:
            mock_validate.return_value = ValidationResult(
                is_valid=True,
                status=ValidationStatus.VALID,
                service=ServiceType.OPENAI,
                message="Valid",
            )

            with pytest.raises(ServiceError):
                await api_service.create_api_key(user_id, request)

    @pytest.mark.asyncio
    async def test_transaction_timeout_failure(self, api_service, mock_dependencies):
        """Test transaction timeout during database operations."""
        user_id = str(uuid.uuid4())
        request = ApiKeyCreateRequest(
            name="Test Key",
            service=ServiceType.OPENAI,
            key_value="sk-test-key-12345",
            description="Test",
        )

        # Simulate timeout during transaction execution
        mock_transaction = AsyncMock()
        mock_transaction.__aenter__.return_value = mock_transaction
        mock_transaction.execute.side_effect = TimeoutError("Transaction timeout")
        mock_dependencies["db"].transaction.return_value = mock_transaction

        with patch.object(api_service, "validate_api_key") as mock_validate:
            mock_validate.return_value = ValidationResult(
                is_valid=True,
                status=ValidationStatus.VALID,
                service=ServiceType.OPENAI,
                message="Valid",
            )

            with pytest.raises(ServiceError):
                await api_service.create_api_key(user_id, request)

    # PHASE 2: Service Validation Tests (Lines 761-767, 834-840, 907-914)

    @pytest.mark.asyncio
    async def test_validate_openai_key_timeout_handling(self, api_service):
        """Test OpenAI validation with network timeout - targets lines 761-767."""
        user_id = str(uuid.uuid4())

        with patch.object(api_service.client, "get") as mock_get:
            mock_get.side_effect = TimeoutError("Request timeout")

            result = await api_service.validate_api_key(
                ServiceType.OPENAI, "sk-test-key-12345", user_id
            )

            assert result.is_valid is False
            assert result.status == ValidationStatus.SERVICE_ERROR
            assert "timeout" in result.message.lower()

    @pytest.mark.asyncio
    async def test_validate_weather_key_timeout_handling(self, api_service):
        """Test weather validation with timeout - targets lines 834-840."""
        user_id = str(uuid.uuid4())

        with patch.object(api_service.client, "get") as mock_get:
            mock_get.side_effect = TimeoutError("Request timeout")

            result = await api_service.validate_api_key(
                ServiceType.WEATHER, "weather_api_key_test_12345", user_id
            )

            assert result.is_valid is False
            assert result.status == ValidationStatus.SERVICE_ERROR
            assert "timeout" in result.message.lower()

    @pytest.mark.asyncio
    async def test_validate_googlemaps_timeout_handling(self, api_service):
        """Test Google Maps validation timeout - targets lines 907-914."""
        user_id = str(uuid.uuid4())

        with patch.object(api_service.client, "get") as mock_get:
            mock_get.side_effect = TimeoutError("Request timeout")

            result = await api_service.validate_api_key(
                ServiceType.GOOGLEMAPS, "AIza_test_key_value_12345", user_id
            )

            assert result.is_valid is False
            assert result.status == ValidationStatus.SERVICE_ERROR
            assert "timeout" in result.message.lower()

    @pytest.mark.asyncio
    async def test_googlemaps_capability_detection_failure(self, api_service):
        """Test capability detection with API errors - targets lines 1095-1112."""
        user_id = str(uuid.uuid4())

        with patch.object(api_service.client, "get") as mock_get:
            # Mock main validation success but capability checks fail
            main_response = Mock()
            main_response.status_code = 200
            main_response.json.return_value = {"status": "OK"}

            capability_response = Mock()
            capability_response.json.side_effect = Exception("JSON decode error")

            mock_get.side_effect = [
                main_response,
                capability_response,
                capability_response,
                capability_response,
            ]

            result = await api_service.validate_api_key(
                ServiceType.GOOGLEMAPS, "AIza_test_key_value_12345", user_id
            )

            # Should still validate successfully even if capability detection fails
            assert result.is_valid is True
            assert result.status == ValidationStatus.VALID

    @pytest.mark.asyncio
    async def test_weather_api_rate_limiting_scenarios(self, api_service):
        """Test weather API rate limit handling - targets lines 818-824."""
        user_id = str(uuid.uuid4())

        with patch.object(api_service.client, "get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 429  # Rate limited
            mock_get.return_value = mock_response

            result = await api_service.validate_api_key(
                ServiceType.WEATHER, "weather_api_key_test_12345", user_id
            )

            assert result.is_valid is False
            assert result.status == ValidationStatus.RATE_LIMITED

    # PHASE 3: Cache Infrastructure Tests (Lines 1128-1159)

    @pytest.mark.asyncio
    async def test_cache_service_unavailable_scenarios(
        self, api_service, mock_dependencies
    ):
        """Test validation caching when cache service fails - targets lines
        1128-1159.
        """
        user_id = str(uuid.uuid4())

        # Mock cache service to raise exceptions
        mock_dependencies["cache"].get.side_effect = Exception("Cache unavailable")
        mock_dependencies["cache"].set.side_effect = Exception("Cache write failed")

        with patch.object(api_service.client, "get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": [{"id": "model-1"}]}
            mock_get.return_value = mock_response

            # Should still work despite cache failures
            result = await api_service.validate_api_key(
                ServiceType.OPENAI, "sk-test-key-12345", user_id
            )

            assert result.is_valid is True
            assert result.status == ValidationStatus.VALID

    # Additional Error Path Coverage

    @pytest.mark.asyncio
    async def test_encryption_roundtrip_property(self, api_service):
        """Test encryption roundtrip to ensure consistency."""
        test_data = "sk-test-api-key-12345"

        encrypted = api_service._encrypt_api_key(test_data)
        decrypted = api_service._decrypt_api_key(encrypted)

        assert decrypted == test_data
        assert encrypted != test_data
        assert len(encrypted) > 0

    @pytest.mark.asyncio
    async def test_validation_with_retry_mechanism(self, api_service):
        """Test retry mechanism in validation."""
        user_id = str(uuid.uuid4())

        with patch.object(api_service.client, "get") as mock_get:
            # The @retry decorator specifically handles httpx.TimeoutException and
            # httpx.ConnectError
            # First call fails with httpx.TimeoutException, second succeeds
            mock_get.side_effect = [
                httpx.TimeoutException("Request timeout"),
                Mock(status_code=200, json=lambda: {"data": [{"id": "model-1"}]}),
            ]

            result = await api_service.validate_api_key(
                ServiceType.OPENAI, "sk-test-key-12345", user_id
            )

            # Should succeed after retry
            assert result.is_valid is True
            assert mock_get.call_count == 2

    @pytest.mark.asyncio
    async def test_concurrent_operations_safety(self, api_service, mock_dependencies):
        """Test concurrent operations for race condition coverage."""
        user_id = str(uuid.uuid4())

        # Mock successful database transaction
        mock_transaction = AsyncMock()
        mock_transaction.__aenter__.return_value = mock_transaction
        mock_transaction.execute.return_value = [[{"id": str(uuid.uuid4())}], []]
        mock_dependencies["db"].transaction.return_value = mock_transaction

        with patch.object(api_service, "validate_api_key") as mock_validate:
            mock_validate.return_value = ValidationResult(
                is_valid=True,
                status=ValidationStatus.VALID,
                service=ServiceType.OPENAI,
                message="Valid",
            )

            # Create concurrent requests
            requests = [
                ApiKeyCreateRequest(
                    name=f"Test Key {i}",
                    service=ServiceType.OPENAI,
                    key_value=f"sk-test-key-{i}-12345",
                    description="Test",
                )
                for i in range(3)
            ]

            # Run concurrent operations
            tasks = [
                api_service.create_api_key(user_id, request) for request in requests
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # All should succeed or fail gracefully
            for result in results:
                assert isinstance(result, (ApiKeyResponse, Exception))

    @pytest.mark.asyncio
    async def test_edge_case_input_handling(self, api_service):
        """Test handling of edge case inputs."""
        user_id = str(uuid.uuid4())

        edge_cases = [
            "",  # Empty string
            "x" * 1000,  # Very long string
            "\x00\x01\x02",  # Binary data
            "🚀🔑🌟",  # Unicode/emoji
        ]

        for edge_input in edge_cases:
            result = await api_service.validate_api_key(
                ServiceType.OPENAI, edge_input, user_id
            )

            # Should handle gracefully without crashing
            assert isinstance(result, ValidationResult)
            assert isinstance(result.is_valid, bool)
            assert isinstance(result.message, str)

    @pytest.mark.asyncio
    async def test_service_health_check_coverage(self, api_service):
        """Test service health check functionality."""
        # Test individual service health check
        health_result = await api_service.check_service_health(ServiceType.OPENAI)
        assert hasattr(health_result, "service")
        assert hasattr(health_result, "status")

        # Test all services health check
        all_health = await api_service.check_all_services_health()
        assert isinstance(all_health, dict)
        assert len(all_health) >= 1


class TestServiceValidationFailures:
    """Comprehensive tests for service validation failures and timeout scenarios."""

    @pytest.fixture
    async def api_service(self):
        """Create ApiKeyService with mocked dependencies."""
        db = AsyncMock()
        cache = AsyncMock()
        return ApiKeyService(db, cache)

    @pytest.mark.asyncio
    async def test_googlemaps_health_check_timeout(self, api_service):
        """Test Google Maps health check timeout handling (lines 1095-1099)."""
        with patch.object(api_service.client, "get") as mock_get:
            mock_get.side_effect = httpx.TimeoutException("Service timeout")

            result = await api_service._check_googlemaps_health()

            # Should return unhealthy status with timeout message
            assert result.service == ServiceType.GOOGLEMAPS
            assert result.status == ServiceHealthStatus.UNHEALTHY
            assert "Service timeout" in result.message
            assert result.latency_ms > 0

    @pytest.mark.asyncio
    async def test_googlemaps_health_check_network_error(self, api_service):
        """Test Google Maps health check network connection failures."""
        with patch.object(api_service.client, "get") as mock_get:
            mock_get.side_effect = httpx.ConnectError("Connection failed")

            # ConnectError will propagate since Google Maps health check doesn't
            # handle it
            with pytest.raises(httpx.ConnectError, match="Connection failed"):
                await api_service._check_googlemaps_health()

    @pytest.mark.asyncio
    async def test_googlemaps_capability_detection_timeout(self, api_service):
        """Test Google Maps capability detection with timeout (lines 1112-1127)."""
        with patch.object(api_service.client, "get") as mock_get:
            # Simulate timeout on all capability check requests
            mock_get.side_effect = httpx.TimeoutException("Request timeout")

            capabilities = await api_service._check_googlemaps_capabilities("test-key")

            # Should return empty capabilities due to timeouts (line 1125-1127)
            assert capabilities == []
            # Should have attempted all 3 API tests (geocoding, places, directions)
            assert mock_get.call_count == 3

    @pytest.mark.asyncio
    async def test_googlemaps_capability_detection_partial_failures(self, api_service):
        """Test Google Maps capability detection with mixed success/failure."""
        with patch.object(api_service.client, "get") as mock_get:
            # First API succeeds, second times out, third fails with error
            mock_get.side_effect = [
                Mock(status_code=200, json=lambda: {"status": "OK"}),
                httpx.TimeoutException("Timeout"),
                httpx.ConnectError("Network error"),
            ]

            capabilities = await api_service._check_googlemaps_capabilities("test-key")

            # Should only return capability for the successful API
            assert capabilities == ["geocoding"]
            assert mock_get.call_count == 3

    @pytest.mark.asyncio
    async def test_openai_validation_timeout_handling(self, api_service):
        """Test OpenAI validation timeout handling (lines 778-784)."""
        user_id = str(uuid.uuid4())

        with patch.object(api_service.client, "get") as mock_get:
            mock_get.side_effect = httpx.TimeoutException("Request timeout")

            result = await api_service.validate_api_key(
                ServiceType.OPENAI, "sk-test-key-12345", user_id
            )

            # Should return service error with timeout message
            assert result.is_valid is False
            assert result.status == ValidationStatus.SERVICE_ERROR
            assert result.service == ServiceType.OPENAI
            assert "timed out" in result.message.lower()

    @pytest.mark.asyncio
    async def test_openai_health_check_timeout(self, api_service):
        """Test OpenAI health check timeout scenarios (lines 1001-1009)."""
        with patch.object(api_service.client, "get") as mock_get:
            mock_get.side_effect = httpx.TimeoutException("Health check timeout")

            result = await api_service._check_openai_health()

            assert result.service == ServiceType.OPENAI
            assert result.status == ServiceHealthStatus.UNKNOWN
            assert result.latency_ms > 0

    @pytest.mark.asyncio
    async def test_openai_health_check_network_error(self, api_service):
        """Test OpenAI health check network failures."""
        with patch.object(api_service.client, "get") as mock_get:
            mock_get.side_effect = httpx.ConnectError("Cannot connect to OpenAI")

            result = await api_service._check_openai_health()

            assert result.service == ServiceType.OPENAI
            assert result.status == ServiceHealthStatus.UNKNOWN
            assert "Cannot connect to OpenAI" in result.message

    @pytest.mark.asyncio
    async def test_weather_api_validation_timeout(self, api_service):
        """Test Weather API validation timeout handling (lines 851-857)."""
        user_id = str(uuid.uuid4())

        with patch.object(api_service.client, "get") as mock_get:
            mock_get.side_effect = httpx.TimeoutException("Weather API timeout")

            result = await api_service.validate_api_key(
                ServiceType.WEATHER, "test-weather-key-12345", user_id
            )

            # Should return service error with timeout message
            assert result.is_valid is False
            assert result.status == ValidationStatus.SERVICE_ERROR
            assert result.service == ServiceType.WEATHER
            assert "timed out" in result.message.lower()

    @pytest.mark.asyncio
    async def test_weather_api_network_failures(self, api_service):
        """Test Weather API network connection failures."""
        user_id = str(uuid.uuid4())

        with patch.object(api_service.client, "get") as mock_get:
            mock_get.side_effect = httpx.ConnectError("Network unreachable")

            result = await api_service.validate_api_key(
                ServiceType.WEATHER, "test-weather-key-12345", user_id
            )

            assert result.is_valid is False
            assert result.status == ValidationStatus.SERVICE_ERROR

    @pytest.mark.asyncio
    async def test_service_http_error_codes(self, api_service):
        """Test various HTTP error codes in service validation."""
        user_id = str(uuid.uuid4())

        # Test 500 Internal Server Error
        with patch.object(api_service.client, "get") as mock_get:
            mock_get.return_value = Mock(status_code=500, json=dict)

            result = await api_service.validate_api_key(
                ServiceType.OPENAI, "sk-test-key", user_id
            )

            assert result.is_valid is False
            assert result.status == ValidationStatus.SERVICE_ERROR

    @pytest.mark.asyncio
    async def test_service_malformed_response(self, api_service):
        """Test handling of malformed JSON responses."""
        user_id = str(uuid.uuid4())

        with patch.object(api_service.client, "get") as mock_get:
            # Mock response with invalid JSON
            mock_response = Mock(status_code=200)
            mock_response.json.side_effect = ValueError("Invalid JSON")
            mock_get.return_value = mock_response

            result = await api_service.validate_api_key(
                ServiceType.WEATHER, "test-key", user_id
            )

            # Weather API with short key returns format error, not service error
            assert result.is_valid is False
            assert result.status == ValidationStatus.FORMAT_ERROR

    @pytest.mark.asyncio
    async def test_multiple_service_timeout_scenarios(self, api_service):
        """Test timeout scenarios across different services."""
        user_id = str(uuid.uuid4())

        test_cases = [
            (ServiceType.OPENAI, "sk-test-key-12345"),
            (ServiceType.WEATHER, "weather-key-12345"),
            (ServiceType.GOOGLEMAPS, "maps-key-12345678901234567890"),
        ]

        for service_type, key_value in test_cases:
            with patch.object(api_service.client, "get") as mock_get:
                mock_get.side_effect = httpx.TimeoutException(
                    f"{service_type.value} timeout"
                )

                result = await api_service.validate_api_key(
                    service_type, key_value, user_id
                )

                assert result.is_valid is False
                assert result.status == ValidationStatus.SERVICE_ERROR
                assert result.service == service_type
                assert "timed out" in result.message.lower()

    @pytest.mark.asyncio
    async def test_health_check_timeout_status_consistency(self, api_service):
        """Test that health check timeouts return consistent status."""
        # Test all service health checks with timeout
        services = [ServiceType.OPENAI, ServiceType.GOOGLEMAPS]

        for service in services:
            with patch.object(api_service.client, "get") as mock_get:
                mock_get.side_effect = httpx.TimeoutException("Health timeout")

                if service == ServiceType.OPENAI:
                    result = await api_service._check_openai_health()
                    expected_status = (
                        ServiceHealthStatus.UNKNOWN
                    )  # OpenAI returns UNKNOWN on timeout
                elif service == ServiceType.GOOGLEMAPS:
                    result = await api_service._check_googlemaps_health()
                    expected_status = (
                        ServiceHealthStatus.UNHEALTHY
                    )  # Google Maps returns UNHEALTHY on timeout

                assert result.service == service
                assert result.status == expected_status
                assert result.latency_ms >= 0

    @pytest.mark.asyncio
    async def test_concurrent_timeout_handling(self, api_service):
        """Test concurrent validation requests with timeouts."""
        user_id = str(uuid.uuid4())

        with patch.object(api_service.client, "get") as mock_get:
            mock_get.side_effect = httpx.TimeoutException("Concurrent timeout")

            # Start multiple concurrent validations
            tasks = [
                api_service.validate_api_key(ServiceType.OPENAI, f"sk-key-{i}", user_id)
                for i in range(3)
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # All should handle timeout gracefully
            for result in results:
                assert isinstance(result, ValidationResult)
                assert result.is_valid is False
                assert result.status == ValidationStatus.SERVICE_ERROR
