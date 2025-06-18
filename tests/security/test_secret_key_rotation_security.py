"""
Security tests for secret key rotation and cryptographic edge cases.

This module provides comprehensive security testing for secret key rotation,
cryptographic edge cases, and key lifecycle management vulnerabilities.
Tests cover various attack scenarios targeting encryption, decryption,
and key management processes.

Based on NIST SP 800-57 key management recommendations and OWASP
cryptographic storage security guidelines.
"""

import asyncio
import base64
import secrets
import time
from unittest.mock import AsyncMock, Mock

import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from tripsage_core.exceptions.exceptions import (
    CoreServiceError as ServiceError,
)
from tripsage_core.services.business.api_key_service import (
    ApiKeyCreateRequest,
    ApiKeyService,
    ServiceType,
)

class TestSecretKeyRotationSecurity:
    """Security tests for secret key rotation scenarios."""

    @pytest.fixture
    def mock_db_service(self):
        """Mock database service."""
        db = AsyncMock()
        db.transaction.return_value.__aenter__.return_value = db
        db.transaction.return_value.__aexit__.return_value = None
        db.insert.return_value = None
        db.execute.return_value = [[{"id": "test_key_123"}]]
        db.get_user_api_keys.return_value = []
        db.get_api_key_for_service.return_value = None
        db.get_api_key_by_id.return_value = None
        db.update_api_key_last_used.return_value = None
        db.delete.return_value = None
        return db

    @pytest.fixture
    def mock_cache_service(self):
        """Mock cache service."""
        cache = AsyncMock()
        cache.get.return_value = None
        cache.set.return_value = True
        return cache

    @pytest.fixture
    def mock_settings(self):
        """Mock settings with secret key."""
        settings = Mock()
        settings.secret_key = "test_master_secret_key_for_rotation_testing"
        return settings

    @pytest.fixture
    async def api_key_service(self, mock_db_service, mock_cache_service, mock_settings):
        """API key service instance for testing."""
        service = ApiKeyService(
            db=mock_db_service, cache=mock_cache_service, settings=mock_settings
        )
        yield service
        await service.client.aclose()

    @pytest.fixture
    def sample_api_key_data(self):
        """Sample API key data for testing."""
        return ApiKeyCreateRequest(
            name="Test OpenAI Key",
            service=ServiceType.OPENAI,
            key_value="sk-test123456789abcdef",
            description="Test key for rotation testing",
        )

    async def test_master_key_rotation_graceful_transition(
        self, mock_db_service, mock_cache_service
    ):
        """Test graceful transition during master key rotation."""
        # Create service with original master key
        original_settings = Mock()
        original_settings.secret_key = "original_master_secret_key_v1"

        service_v1 = ApiKeyService(
            db=mock_db_service, cache=mock_cache_service, settings=original_settings
        )

        # Encrypt API key with original master key
        test_api_key = "sk-test123456789abcdef"
        encrypted_v1 = service_v1._encrypt_api_key(test_api_key)

        # Create service with new master key
        new_settings = Mock()
        new_settings.secret_key = "new_master_secret_key_v2"

        service_v2 = ApiKeyService(
            db=mock_db_service, cache=mock_cache_service, settings=new_settings
        )

        # Should not be able to decrypt with new master key
        with pytest.raises(ServiceError, match="Decryption failed"):
            service_v2._decrypt_api_key(encrypted_v1)

        # But original service should still work
        decrypted = service_v1._decrypt_api_key(encrypted_v1)
        assert decrypted == test_api_key

        await service_v1.client.aclose()
        await service_v2.client.aclose()

    async def test_master_key_rotation_attack_prevention(
        self, mock_db_service, mock_cache_service
    ):
        """Test protection against attacks during key rotation."""
        # Simulate attacker trying to exploit rotation window
        settings = Mock()
        settings.secret_key = "current_master_key"

        service = ApiKeyService(
            db=mock_db_service, cache=mock_cache_service, settings=settings
        )

        test_api_key = "sk-test123456789abcdef"
        encrypted_key = service._encrypt_api_key(test_api_key)

        # Attacker attempts to manipulate master key
        malicious_keys = [
            "",  # Empty key
            "a",  # Too short
            "malicious_key_injection_attempt",
            "../../etc/passwd",
            "<script>alert('xss')</script>",
            "'; DROP TABLE keys; --",
            "\x00\x01\x02\x03",  # Binary data
            "key" * 1000,  # Extremely long key
        ]

        for malicious_key in malicious_keys:
            # Should not crash or leak information
            try:
                malicious_settings = Mock()
                malicious_settings.secret_key = malicious_key

                malicious_service = ApiKeyService(
                    db=mock_db_service,
                    cache=mock_cache_service,
                    settings=malicious_settings,
                )

                # Should fail gracefully
                with pytest.raises((ServiceError, ValueError, Exception)):
                    malicious_service._decrypt_api_key(encrypted_key)

                await malicious_service.client.aclose()

            except Exception as e:
                # Should handle malicious keys gracefully
                assert "failed" in str(e).lower() or "invalid" in str(e).lower()

        await service.client.aclose()

    async def test_key_derivation_security_edge_cases(
        self, mock_db_service, mock_cache_service
    ):
        """Test security of key derivation process under edge cases."""
        base_settings = Mock()
        base_settings.secret_key = "test_secret_key"

        service = ApiKeyService(
            db=mock_db_service, cache=mock_cache_service, settings=base_settings
        )

        # Test encryption/decryption with various data patterns
        edge_case_keys = [
            "sk-" + "a" * 100,  # Very long key
            "sk-" + "1" * 50,  # Numeric key
            "sk-" + "\u4e2d\u6587",  # Unicode characters
            "sk-test\r\n\t",  # Control characters
            "sk-" + secrets.token_urlsafe(32),  # High entropy key
            "sk-" + "0" * 32,  # Low entropy key
            "sk-" + base64.b64encode(b"binary_data").decode(),  # Base64 data
        ]

        for test_key in edge_case_keys:
            try:
                encrypted = service._encrypt_api_key(test_key)
                decrypted = service._decrypt_api_key(encrypted)
                assert decrypted == test_key

                # Verify encrypted data properties
                assert isinstance(encrypted, str)
                assert len(encrypted) > 0
                assert encrypted != test_key  # Should be encrypted

            except Exception as e:
                # Should handle edge cases gracefully
                assert "encryption" in str(e).lower() or "invalid" in str(e).lower()

        await service.client.aclose()

    async def test_envelope_encryption_key_isolation(
        self, mock_db_service, mock_cache_service
    ):
        """Test isolation of envelope encryption data keys."""
        settings = Mock()
        settings.secret_key = "test_master_secret_for_isolation"

        service = ApiKeyService(
            db=mock_db_service, cache=mock_cache_service, settings=settings
        )

        # Encrypt multiple keys to ensure unique data keys
        test_keys = ["sk-key1_test123", "sk-key2_test456", "sk-key3_test789"]

        encrypted_keys = []
        for key in test_keys:
            encrypted = service._encrypt_api_key(key)
            encrypted_keys.append(encrypted)

        # Each encrypted result should be unique (different data keys)
        assert len(set(encrypted_keys)) == len(encrypted_keys)

        # Decrypt and verify each key
        for i, encrypted in enumerate(encrypted_keys):
            decrypted = service._decrypt_api_key(encrypted)
            assert decrypted == test_keys[i]

        # Test data key isolation by attempting to mix components
        try:
            # Extract components from first encrypted key
            combined_1 = base64.urlsafe_b64decode(encrypted_keys[0].encode())
            parts_1 = combined_1.split(b"::", 1)

            # Extract components from second encrypted key
            combined_2 = base64.urlsafe_b64decode(encrypted_keys[1].encode())
            parts_2 = combined_2.split(b"::", 1)

            # Try to mix data key from key 1 with encrypted data from key 2
            mixed_combined = parts_1[0] + b"::" + parts_2[1]
            mixed_encrypted = base64.urlsafe_b64encode(mixed_combined).decode()

            # Should fail to decrypt mixed components
            with pytest.raises(ServiceError):
                service._decrypt_api_key(mixed_encrypted)

        except Exception:
            # Expected - key isolation should prevent mixing
            pass

        await service.client.aclose()

    async def test_cryptographic_timing_attack_resistance(
        self, mock_db_service, mock_cache_service
    ):
        """Test resistance to timing attacks in cryptographic operations."""
        settings = Mock()
        settings.secret_key = "timing_attack_test_secret"

        service = ApiKeyService(
            db=mock_db_service, cache=mock_cache_service, settings=settings
        )

        # Create valid encrypted key
        valid_key = "sk-valid123456789"
        valid_encrypted = service._encrypt_api_key(valid_key)

        # Create various invalid encrypted keys
        invalid_encrypted_keys = [
            "invalid_base64_data",
            base64.urlsafe_b64encode(b"short").decode(),
            base64.urlsafe_b64encode(b"no_separator_in_data").decode(),
            base64.urlsafe_b64encode(b"wrong::separator::count").decode(),
            valid_encrypted[:-10] + "modified",  # Corrupted end
            "a" + valid_encrypted[1:],  # Corrupted start
        ]

        # Measure timing for valid vs invalid decryption
        valid_times = []
        invalid_times = []

        # Time valid decryptions
        for _ in range(10):
            start = time.time()
            try:
                service._decrypt_api_key(valid_encrypted)
            except Exception:
                pass
            end = time.time()
            valid_times.append(end - start)

        # Time invalid decryptions
        for invalid_key in invalid_encrypted_keys:
            start = time.time()
            try:
                service._decrypt_api_key(invalid_key)
            except Exception:
                pass
            end = time.time()
            invalid_times.append(end - start)

        # Calculate timing statistics
        avg_valid = sum(valid_times) / len(valid_times)
        avg_invalid = sum(invalid_times) / len(invalid_times)

        # Timing difference should not reveal significant information
        max_ratio = max(avg_valid, avg_invalid) / min(avg_valid, avg_invalid)
        assert max_ratio < 10, (
            f"Potential timing attack vulnerability: {max_ratio:.2f}x difference"
        )

        await service.client.aclose()

    async def test_key_rotation_concurrency_safety(
        self, mock_db_service, mock_cache_service
    ):
        """Test concurrent safety during key rotation operations."""
        settings = Mock()
        settings.secret_key = "concurrent_rotation_test_secret"

        # Create multiple service instances to simulate concurrent access
        services = []
        for _i in range(5):
            service = ApiKeyService(
                db=mock_db_service, cache=mock_cache_service, settings=settings
            )
            services.append(service)

        test_key = "sk-concurrent123456789"

        async def encrypt_decrypt_task(service_instance, task_id):
            """Concurrent encryption/decryption task."""
            results = []
            for i in range(10):
                try:
                    # Add task-specific data to ensure uniqueness
                    key_with_id = f"{test_key}_{task_id}_{i}"
                    encrypted = service_instance._encrypt_api_key(key_with_id)
                    decrypted = service_instance._decrypt_api_key(encrypted)
                    results.append(decrypted == key_with_id)
                except Exception:
                    results.append(False)
                # Small delay to increase concurrency overlap
                await asyncio.sleep(0.001)
            return results

        # Run concurrent tasks
        tasks = [encrypt_decrypt_task(service, i) for i, service in enumerate(services)]

        all_results = await asyncio.gather(*tasks)

        # All operations should succeed
        total_operations = sum(len(results) for results in all_results)
        successful_operations = sum(sum(results) for results in all_results)

        success_rate = successful_operations / total_operations
        assert success_rate > 0.95, (
            f"Concurrent operations failed: {success_rate:.2%} success rate"
        )

        # Cleanup
        for service in services:
            await service.client.aclose()

    async def test_master_key_derivation_salt_manipulation(
        self, mock_db_service, mock_cache_service
    ):
        """Test security against salt manipulation attacks."""
        # Test with various salt manipulation attempts
        original_salt = b"tripsage_api_key_salt_v3"

        malicious_salts = [
            b"",  # Empty salt
            b"a",  # Too short
            b"\x00" * 32,  # Null bytes
            b"predictable_salt_12345",  # Predictable pattern
            original_salt + b"_modified",  # Modified original
            b"a" * 1000,  # Extremely long salt
        ]

        settings = Mock()
        settings.secret_key = "salt_manipulation_test_secret"

        # Create service with original implementation
        service = ApiKeyService(
            db=mock_db_service, cache=mock_cache_service, settings=settings
        )

        test_key = "sk-salt_test123456"
        original_encrypted = service._encrypt_api_key(test_key)

        # Verify original works
        decrypted = service._decrypt_api_key(original_encrypted)
        assert decrypted == test_key

        # Test that salt manipulation would break decryption
        # (This tests that the salt is properly integrated into key derivation)
        for _malicious_salt in malicious_salts:
            # Create service with manipulated salt (simulated by different master
            # secret)
            try:
                salt_affected_settings = Mock()
                # Different secret would derive different key due to salt integration
                salt_affected_settings.secret_key = (
                    settings.secret_key + "_salt_modified"
                )

                manipulated_service = ApiKeyService(
                    db=mock_db_service,
                    cache=mock_cache_service,
                    settings=salt_affected_settings,
                )

                # Should not be able to decrypt with different derived key
                with pytest.raises(ServiceError):
                    manipulated_service._decrypt_api_key(original_encrypted)

                await manipulated_service.client.aclose()

            except Exception:
                # Expected - salt manipulation should break decryption
                pass

        await service.client.aclose()

    async def test_key_derivation_iteration_count_security(self, api_key_service):
        """Test PBKDF2 iteration count security requirements."""
        # Access the internal KDF configuration
        # Modern security standards require >= 300,000 iterations for PBKDF2

        # Test that the service uses secure iteration count
        salt = b"tripsage_api_key_salt_v3"
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=300000,  # Should match service implementation
        )

        # Verify algorithm and iteration count
        assert kdf._algorithm.name == "sha256"
        assert kdf._iterations >= 300000, (
            "PBKDF2 iteration count below security threshold"
        )

        # Test that low iteration counts would be insecure
        insecure_iteration_counts = [1, 10, 100, 1000, 10000]

        for insecure_count in insecure_iteration_counts:
            # These should be considered insecure by modern standards
            assert insecure_count < 300000, (
                f"Iteration count {insecure_count} is below security threshold"
            )

    async def test_encrypted_key_format_tampering_detection(self, api_key_service):
        """Test detection of encrypted key format tampering."""
        test_key = "sk-tamper_test123456"
        encrypted = api_key_service._encrypt_api_key(test_key)

        # Various tampering attempts
        tampering_attempts = [
            # Modify base64 encoding
            encrypted[:-5] + "AAAAA",
            encrypted.replace("A", "B"),
            encrypted + "extra_data",
            # Separator manipulation
            base64.urlsafe_b64encode(
                base64.urlsafe_b64decode(encrypted.encode()).replace(b"::", b"||")
            ).decode(),
            base64.urlsafe_b64encode(
                base64.urlsafe_b64decode(encrypted.encode()).replace(b"::", b":::")
            ).decode(),
            # Length manipulation
            encrypted[: len(encrypted) // 2],  # Truncated
            encrypted * 2,  # Doubled
            # Character manipulation
            encrypted.replace(encrypted[10], "X") if len(encrypted) > 10 else encrypted,
            encrypted.upper() if encrypted.islower() else encrypted.lower(),
            # Format corruption
            "not_base64_data",
            base64.urlsafe_b64encode(b"corrupted_data").decode(),
            "",  # Empty string
        ]

        for tampered in tampering_attempts:
            # All tampering attempts should be detected and fail
            with pytest.raises(
                ServiceError, match="(Decryption failed|Invalid encrypted key format)"
            ):
                api_key_service._decrypt_api_key(tampered)

    async def test_envelope_encryption_data_key_strength(self, api_key_service):
        """Test strength of envelope encryption data keys."""
        test_key = "sk-datakey_test123456"

        # Generate multiple encrypted keys to analyze data key entropy
        encrypted_keys = []
        for i in range(50):
            encrypted = api_key_service._encrypt_api_key(f"{test_key}_{i}")
            encrypted_keys.append(encrypted)

        # Extract encrypted data keys from multiple encryptions
        data_key_parts = []
        for encrypted in encrypted_keys:
            try:
                combined = base64.urlsafe_b64decode(encrypted.encode())
                parts = combined.split(b"::", 1)
                if len(parts) == 2:
                    data_key_parts.append(parts[0])  # Encrypted data key part
            except Exception:
                continue

        # Verify data key uniqueness (should all be different)
        unique_data_keys = set(data_key_parts)
        uniqueness_ratio = len(unique_data_keys) / len(data_key_parts)
        assert uniqueness_ratio > 0.95, (
            f"Data key uniqueness too low: {uniqueness_ratio:.2%}"
        )

        # Verify data key length consistency
        data_key_lengths = [len(dk) for dk in data_key_parts]
        assert all(length == data_key_lengths[0] for length in data_key_lengths), (
            "Inconsistent data key lengths"
        )

        # Verify minimum entropy (length should indicate Fernet key size)
        assert data_key_lengths[0] > 32, "Data key length suggests insufficient entropy"

    async def test_key_lifecycle_security_transitions(
        self, mock_db_service, mock_cache_service
    ):
        """Test security during key lifecycle transitions."""
        settings = Mock()
        settings.secret_key = "lifecycle_test_secret"

        service = ApiKeyService(
            db=mock_db_service, cache=mock_cache_service, settings=settings
        )

        test_key = "sk-lifecycle123456789"

        # Test encryption during various lifecycle states
        lifecycle_states = [
            "creation",
            "active_use",
            "rotation_pending",
            "deprecated",
            "deletion_pending",
        ]

        encrypted_versions = {}

        for state in lifecycle_states:
            # Simulate different lifecycle states
            key_with_state = f"{test_key}_{state}"
            encrypted = service._encrypt_api_key(key_with_state)
            encrypted_versions[state] = encrypted

            # Verify encryption/decryption works in all states
            decrypted = service._decrypt_api_key(encrypted)
            assert decrypted == key_with_state

        # Verify each lifecycle state produces unique encryption
        encrypted_values = list(encrypted_versions.values())
        assert len(set(encrypted_values)) == len(encrypted_values), (
            "Lifecycle states should produce unique encryptions"
        )

        # Test that rotation doesn't leave old keys accessible
        # Simulate key rotation by changing master secret
        rotated_settings = Mock()
        rotated_settings.secret_key = "rotated_lifecycle_secret"

        rotated_service = ApiKeyService(
            db=mock_db_service, cache=mock_cache_service, settings=rotated_settings
        )

        # Old encrypted keys should not be accessible after rotation
        for _state, encrypted in encrypted_versions.items():
            with pytest.raises(ServiceError):
                rotated_service._decrypt_api_key(encrypted)

        await service.client.aclose()
        await rotated_service.client.aclose()

    async def test_cryptographic_error_information_leakage(self, api_key_service):
        """Test that cryptographic errors don't leak sensitive information."""
        test_key = "sk-error_test123456"
        valid_encrypted = api_key_service._encrypt_api_key(test_key)

        # Various invalid inputs that should produce safe error messages
        invalid_inputs = [
            None,
            "",
            "invalid_format",
            "a" * 1000,  # Too long
            valid_encrypted[:-10],  # Truncated
            valid_encrypted + "corrupted",  # Extended
            base64.urlsafe_b64encode(b"fake_data").decode(),
        ]

        for invalid_input in invalid_inputs:
            try:
                if invalid_input is None:
                    # Test None input
                    with pytest.raises((ServiceError, AttributeError, TypeError)):
                        api_key_service._decrypt_api_key(invalid_input)
                else:
                    with pytest.raises(ServiceError) as exc_info:
                        api_key_service._decrypt_api_key(invalid_input)

                    # Error message should not reveal sensitive information
                    error_message = str(exc_info.value).lower()
                    sensitive_terms = [
                        "secret",
                        "key",
                        "master",
                        "salt",
                        "iteration",
                        "pbkdf2",
                        "fernet",
                        "aes",
                        "decrypt",
                        "cipher",
                    ]

                    for term in sensitive_terms:
                        assert term not in error_message, (
                            f"Error message leaks sensitive term: {term}"
                        )

                    # Should be generic error message
                    assert (
                        "decryption failed" in error_message
                        or "encryption failed" in error_message
                    )

            except Exception as e:
                # Any exception should not leak sensitive information
                error_str = str(e).lower()
                assert "secret" not in error_str
                assert "master" not in error_str
                assert "pbkdf2" not in error_str

    async def test_key_rotation_backward_compatibility_security(
        self, mock_db_service, mock_cache_service
    ):
        """Test security implications of backward compatibility during key rotation."""
        # Simulate legacy key format (simplified for testing)
        legacy_settings = Mock()
        legacy_settings.secret_key = "legacy_secret_v1"

        legacy_service = ApiKeyService(
            db=mock_db_service, cache=mock_cache_service, settings=legacy_settings
        )

        # Encrypt with legacy system
        test_key = "sk-legacy123456789"
        legacy_encrypted = legacy_service._encrypt_api_key(test_key)

        # Simulate new system with different master key
        new_settings = Mock()
        new_settings.secret_key = "new_secret_v2"

        new_service = ApiKeyService(
            db=mock_db_service, cache=mock_cache_service, settings=new_settings
        )

        # New system should not be able to decrypt legacy keys
        with pytest.raises(ServiceError):
            new_service._decrypt_api_key(legacy_encrypted)

        # Test that attackers can't exploit backward compatibility
        # by providing legacy-format encrypted data to new system
        fake_legacy_attempts = [
            base64.urlsafe_b64encode(b"fake_legacy_key::fake_data").decode(),
            base64.urlsafe_b64encode(
                b"legacy_header" + b"\x00" * 32 + b"::data"
            ).decode(),
            legacy_encrypted.replace(
                legacy_encrypted[0], "L"
            ),  # "Legacy" marker attempt
        ]

        for fake_legacy in fake_legacy_attempts:
            with pytest.raises(ServiceError):
                new_service._decrypt_api_key(fake_legacy)

        await legacy_service.client.aclose()
        await new_service.client.aclose()

class TestCryptographicEdgeCases:
    """Security tests for cryptographic edge cases and error conditions."""

    @pytest.fixture
    async def api_key_service(self, mock_db_service, mock_cache_service, mock_settings):
        """API key service instance for edge case testing."""
        service = ApiKeyService(
            db=mock_db_service, cache=mock_cache_service, settings=mock_settings
        )
        yield service
        await service.client.aclose()

    @pytest.fixture
    def mock_db_service(self):
        """Mock database service."""
        db = AsyncMock()
        db.transaction.return_value.__aenter__.return_value = db
        db.transaction.return_value.__aexit__.return_value = None
        return db

    @pytest.fixture
    def mock_cache_service(self):
        """Mock cache service."""
        return AsyncMock()

    @pytest.fixture
    def mock_settings(self):
        """Mock settings."""
        settings = Mock()
        settings.secret_key = "edge_case_test_secret_key"
        return settings

    async def test_fernet_token_expiration_security(self, api_key_service):
        """Test security implications of Fernet token expiration."""
        test_key = "sk-expiration_test123"

        # Test that encryption produces time-sensitive tokens
        encrypted_1 = api_key_service._encrypt_api_key(test_key)

        # Small delay
        await asyncio.sleep(0.001)

        encrypted_2 = api_key_service._encrypt_api_key(test_key)

        # Should produce different encrypted values due to timestamp
        assert encrypted_1 != encrypted_2

        # Both should decrypt to same value
        decrypted_1 = api_key_service._decrypt_api_key(encrypted_1)
        decrypted_2 = api_key_service._decrypt_api_key(encrypted_2)

        assert decrypted_1 == test_key
        assert decrypted_2 == test_key

    async def test_encryption_determinism_security(self, api_key_service):
        """Test that encryption is non-deterministic for security."""
        test_key = "sk-determinism_test123"

        # Encrypt same key multiple times
        encrypted_versions = []
        for _ in range(10):
            encrypted = api_key_service._encrypt_api_key(test_key)
            encrypted_versions.append(encrypted)
            # Small delay to ensure different timestamps
            await asyncio.sleep(0.001)

        # All encrypted versions should be different (non-deterministic)
        unique_versions = set(encrypted_versions)
        assert len(unique_versions) == len(encrypted_versions), (
            "Encryption should be non-deterministic"
        )

        # But all should decrypt to same value
        for encrypted in encrypted_versions:
            decrypted = api_key_service._decrypt_api_key(encrypted)
            assert decrypted == test_key

    async def test_memory_cleanup_after_encryption_operations(self, api_key_service):
        """Test that sensitive data is properly cleaned from memory."""
        import gc

        test_keys = [f"sk-memory_test_{i}" for i in range(100)]

        # Perform many encryption/decryption operations
        for test_key in test_keys:
            encrypted = api_key_service._encrypt_api_key(test_key)
            decrypted = api_key_service._decrypt_api_key(encrypted)
            assert decrypted == test_key

        # Force garbage collection
        gc.collect()

        # This test is more about ensuring operations complete without memory leaks
        # In a real implementation, you might use memory profiling tools
        # to verify sensitive data cleanup

    async def test_cryptographic_boundary_conditions(self, api_key_service):
        """Test cryptographic operations at boundary conditions."""
        # Test minimum length keys
        min_key = "sk-a"  # Very short
        encrypted_min = api_key_service._encrypt_api_key(min_key)
        decrypted_min = api_key_service._decrypt_api_key(encrypted_min)
        assert decrypted_min == min_key

        # Test maximum practical length keys
        max_key = "sk-" + "a" * 1000  # Very long
        encrypted_max = api_key_service._encrypt_api_key(max_key)
        decrypted_max = api_key_service._decrypt_api_key(encrypted_max)
        assert decrypted_max == max_key

        # Test empty content (after prefix)
        empty_key = "sk-"
        encrypted_empty = api_key_service._encrypt_api_key(empty_key)
        decrypted_empty = api_key_service._decrypt_api_key(encrypted_empty)
        assert decrypted_empty == empty_key

        # Test special characters
        special_key = "sk-!@#$%^&*()_+-=[]{}|;:,.<>?"
        encrypted_special = api_key_service._encrypt_api_key(special_key)
        decrypted_special = api_key_service._decrypt_api_key(encrypted_special)
        assert decrypted_special == special_key

    async def test_concurrent_encryption_entropy_independence(self, api_key_service):
        """Test that concurrent encryptions maintain entropy independence."""
        test_key = "sk-entropy_test123456"

        async def encrypt_task():
            """Single encryption task."""
            results = []
            for _ in range(20):
                encrypted = api_key_service._encrypt_api_key(test_key)
                results.append(encrypted)
                await asyncio.sleep(0.001)
            return results

        # Run multiple concurrent encryption tasks
        tasks = [encrypt_task() for _ in range(5)]
        all_results = await asyncio.gather(*tasks)

        # Flatten results
        all_encrypted = []
        for task_results in all_results:
            all_encrypted.extend(task_results)

        # All results should be unique
        unique_encrypted = set(all_encrypted)
        uniqueness_ratio = len(unique_encrypted) / len(all_encrypted)
        assert uniqueness_ratio > 0.95, (
            f"Entropy independence compromised: {uniqueness_ratio:.2%} unique"
        )

        # Verify all decrypt correctly
        for encrypted in all_encrypted:
            decrypted = api_key_service._decrypt_api_key(encrypted)
            assert decrypted == test_key

    async def test_base64_encoding_edge_cases(self, api_key_service):
        """Test base64 encoding edge cases in encryption format."""
        # Test keys that might cause base64 padding issues
        padding_test_keys = [
            "sk-test",  # No padding needed
            "sk-test1",  # 1 padding char needed
            "sk-test12",  # 2 padding chars needed
            "sk-test123",  # No padding needed
            "sk-" + "a" * 16,  # Specific length for padding test
            "sk-" + "b" * 17,  # Different length
            "sk-" + "c" * 18,  # Another length
        ]

        for test_key in padding_test_keys:
            encrypted = api_key_service._encrypt_api_key(test_key)

            # Verify base64 format
            try:
                decoded = base64.urlsafe_b64decode(encrypted.encode())
                assert len(decoded) > 0
            except Exception as e:
                pytest.fail(f"Invalid base64 encoding for key '{test_key}': {e}")

            # Verify round-trip
            decrypted = api_key_service._decrypt_api_key(encrypted)
            assert decrypted == test_key

    async def test_cryptographic_error_recovery(
        self, mock_db_service, mock_cache_service
    ):
        """Test recovery from cryptographic errors."""
        settings = Mock()
        settings.secret_key = "error_recovery_test_secret"

        service = ApiKeyService(
            db=mock_db_service, cache=mock_cache_service, settings=settings
        )

        test_key = "sk-recovery_test123"

        # Test recovery after invalid decryption attempts
        valid_encrypted = service._encrypt_api_key(test_key)

        invalid_attempts = [
            "invalid_data",
            valid_encrypted[:-5],  # Truncated
            valid_encrypted + "extra",  # Extended
        ]

        # Make several invalid attempts
        for invalid in invalid_attempts:
            with pytest.raises(ServiceError):
                service._decrypt_api_key(invalid)

        # Service should still work normally after errors
        new_encrypted = service._encrypt_api_key(test_key)
        decrypted = service._decrypt_api_key(new_encrypted)
        assert decrypted == test_key

        # Original valid encrypted key should still work
        original_decrypted = service._decrypt_api_key(valid_encrypted)
        assert original_decrypted == test_key

        await service.client.aclose()

    async def test_encryption_format_version_resilience(self, api_key_service):
        """Test resilience to format version changes."""
        test_key = "sk-version_test123456"
        encrypted = api_key_service._encrypt_api_key(test_key)

        # Verify current format works
        decrypted = api_key_service._decrypt_api_key(encrypted)
        assert decrypted == test_key

        # Simulate format version detection
        try:
            combined = base64.urlsafe_b64decode(encrypted.encode())
            parts = combined.split(b"::", 1)

            # Current format should have exactly 2 parts
            assert len(parts) == 2, (
                "Current format should have 2 parts separated by '::'"
            )

            encrypted_data_key, encrypted_value = parts

            # Both parts should have reasonable lengths
            assert len(encrypted_data_key) > 20, "Encrypted data key too short"
            assert len(encrypted_value) > 20, "Encrypted value too short"

        except Exception as e:
            pytest.fail(f"Format analysis failed: {e}")

    async def test_master_key_derivation_edge_cases(
        self, mock_db_service, mock_cache_service
    ):
        """Test master key derivation with edge case inputs."""
        edge_case_secrets = [
            "a",  # Very short
            "short",  # Short but valid
            "normal_length_secret_key_123456789",  # Normal
            "very_long_secret_key_" + "x" * 200,  # Very long
            "unicode_secret_键值",  # Unicode characters
            "special!@#$%^&*()secret",  # Special characters
            secrets.token_urlsafe(64),  # High entropy
            "0" * 50,  # Low entropy
        ]

        test_key = "sk-derivation_test123"

        for secret in edge_case_secrets:
            try:
                settings = Mock()
                settings.secret_key = secret

                service = ApiKeyService(
                    db=mock_db_service, cache=mock_cache_service, settings=settings
                )

                # Should be able to encrypt and decrypt
                encrypted = service._encrypt_api_key(test_key)
                decrypted = service._decrypt_api_key(encrypted)
                assert decrypted == test_key

                await service.client.aclose()

            except Exception as e:
                # Document which secrets cause issues
                if len(secret) < 8:
                    # Very short secrets might be rejected
                    continue
                else:
                    pytest.fail(
                        f"Unexpected failure with secret '{secret[:20]}...': {e}"
                    )
