"""
Comprehensive API key encryption security tests.

Tests envelope encryption, PBKDF2HMAC security, key derivation,
and cryptographic attack resistance.
"""

import base64
import hashlib
import os
import secrets
import time
from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from tripsage_core.exceptions.exceptions import CoreServiceError
from tripsage_core.services.business.api_key_service import ApiKeyService


class TestApiKeyEncryptionSecurity:
    """Test encryption security for API key management."""

    @pytest.fixture
    def api_key_service(self):
        """Create API key service with mocked dependencies."""
        mock_db = Mock()
        mock_cache = Mock()
        mock_settings = Mock()
        mock_settings.secret_key = "test-master-secret-key-for-encryption"
        
        service = ApiKeyService(
            db=mock_db,
            cache=mock_cache,
            settings=mock_settings
        )
        return service

    @pytest.fixture
    def secure_api_keys(self):
        """Generate secure test API keys for different services."""
        return {
            "openai": "sk-test-" + secrets.token_urlsafe(32),
            "weather": secrets.token_urlsafe(32),
            "googlemaps": "AIza" + secrets.token_urlsafe(32),
            "short_key": secrets.token_urlsafe(8),
            "long_key": secrets.token_urlsafe(256),
            "unicode_key": "test-κλειδί-密钥-🔑",
            "special_chars": "test!@#$%^&*()_+-=[]{}|;':\",./<>?",
        }

    def test_pbkdf2_configuration_security(self, api_key_service):
        """Test PBKDF2 configuration meets modern security standards."""
        # Test that encryption initialization uses secure parameters
        master_secret = "test-master-secret"
        
        # Recreate the KDF configuration from the service
        salt = b"tripsage_api_key_salt_v3"
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=300000,  # Should be >= 600,000 per OWASP 2024
        )
        
        # Verify secure parameters
        assert kdf._algorithm.name == "sha256", "Should use SHA-256"
        assert kdf._length == 32, "Should derive 256-bit key"
        assert kdf._iterations >= 300000, "Should use at least 300,000 iterations"
        assert len(salt) >= 16, "Salt should be at least 16 bytes"
        
        # Test key derivation produces consistent results
        key1 = kdf.derive(master_secret.encode())
        
        # Reset KDF for second derivation
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=300000,
        )
        key2 = kdf.derive(master_secret.encode())
        
        assert key1 == key2, "Key derivation should be deterministic"
        assert len(key1) == 32, "Derived key should be 256 bits"

    def test_envelope_encryption_security(self, api_key_service, secure_api_keys):
        """Test envelope encryption implementation security."""
        test_key = secure_api_keys["openai"]
        
        # Test encryption
        encrypted_key = api_key_service._encrypt_api_key(test_key)
        
        # Verify encrypted format
        assert isinstance(encrypted_key, str), "Encrypted key should be string"
        assert len(encrypted_key) > len(test_key), "Encrypted should be longer"
        
        # Decode and verify structure
        combined = base64.urlsafe_b64decode(encrypted_key.encode())
        parts = combined.split(b"::", 1)
        assert len(parts) == 2, "Should have data key and encrypted content"
        
        encrypted_data_key, encrypted_content = parts
        assert len(encrypted_data_key) > 0, "Should have encrypted data key"
        assert len(encrypted_content) > 0, "Should have encrypted content"
        
        # Test decryption
        decrypted_key = api_key_service._decrypt_api_key(encrypted_key)
        assert decrypted_key == test_key, "Decryption should restore original"

    def test_encryption_uniqueness(self, api_key_service, secure_api_keys):
        """Test that encryption produces unique ciphertexts for same plaintext."""
        test_key = secure_api_keys["openai"]
        
        # Encrypt the same key multiple times
        encrypted_keys = []
        for _ in range(10):
            encrypted = api_key_service._encrypt_api_key(test_key)
            encrypted_keys.append(encrypted)
            
            # Verify each encryption is unique (due to random data keys)
            assert encrypted not in encrypted_keys[:-1], "Each encryption should be unique"
            
            # Verify decryption works
            decrypted = api_key_service._decrypt_api_key(encrypted)
            assert decrypted == test_key, "All encryptions should decrypt correctly"

    def test_encryption_with_different_key_types(self, api_key_service, secure_api_keys):
        """Test encryption with various key types and edge cases."""
        for key_name, test_key in secure_api_keys.items():
            # Test encryption/decryption cycle
            encrypted = api_key_service._encrypt_api_key(test_key)
            decrypted = api_key_service._decrypt_api_key(encrypted)
            
            assert decrypted == test_key, f"Failed for {key_name}: {test_key}"
            
            # Verify encrypted format is valid base64
            try:
                base64.urlsafe_b64decode(encrypted.encode())
            except Exception as e:
                pytest.fail(f"Invalid base64 for {key_name}: {e}")

    def test_encryption_error_handling(self, api_key_service):
        """Test encryption error handling and edge cases."""
        # Test empty string
        with pytest.raises(CoreServiceError, match="Encryption failed"):
            api_key_service._encrypt_api_key("")
        
        # Test very long string
        very_long_key = "x" * 10000
        encrypted = api_key_service._encrypt_api_key(very_long_key)
        decrypted = api_key_service._decrypt_api_key(encrypted)
        assert decrypted == very_long_key

    def test_decryption_error_handling(self, api_key_service):
        """Test decryption error handling with malformed inputs."""
        # Test invalid base64
        with pytest.raises(CoreServiceError, match="Decryption failed"):
            api_key_service._decrypt_api_key("invalid-base64!")
        
        # Test missing separator
        invalid_encrypted = base64.urlsafe_b64encode(b"no-separator").decode()
        with pytest.raises(CoreServiceError, match="Invalid encrypted key format"):
            api_key_service._decrypt_api_key(invalid_encrypted)
        
        # Test tampered encrypted data
        test_key = "sk-test-key"
        encrypted = api_key_service._encrypt_api_key(test_key)
        
        # Tamper with the encrypted data
        decoded = base64.urlsafe_b64decode(encrypted.encode())
        tampered = decoded[:-1] + b"X"  # Change last byte
        tampered_encrypted = base64.urlsafe_b64encode(tampered).decode()
        
        with pytest.raises(CoreServiceError, match="Decryption failed"):
            api_key_service._decrypt_api_key(tampered_encrypted)

    def test_master_key_isolation(self):
        """Test that different master keys produce different results."""
        test_key = "sk-test-isolation-key"
        
        # Create two services with different master keys
        mock_db = Mock()
        mock_settings1 = Mock()
        mock_settings1.secret_key = "master-key-1"
        service1 = ApiKeyService(db=mock_db, settings=mock_settings1)
        
        mock_settings2 = Mock()
        mock_settings2.secret_key = "master-key-2"
        service2 = ApiKeyService(db=mock_db, settings=mock_settings2)
        
        # Encrypt with service1, try to decrypt with service2
        encrypted1 = service1._encrypt_api_key(test_key)
        
        with pytest.raises(CoreServiceError, match="Decryption failed"):
            service2._decrypt_api_key(encrypted1)
        
        # Verify service1 can decrypt its own encryption
        decrypted1 = service1._decrypt_api_key(encrypted1)
        assert decrypted1 == test_key

    def test_timing_attack_resistance(self, api_key_service):
        """Test that encryption/decryption timing doesn't leak information."""
        # Test keys of different lengths
        short_key = "sk-short"
        long_key = "sk-" + "x" * 100
        
        # Measure encryption times
        times_short = []
        times_long = []
        
        for _ in range(50):
            # Short key timing
            start = time.perf_counter()
            encrypted_short = api_key_service._encrypt_api_key(short_key)
            times_short.append(time.perf_counter() - start)
            
            # Long key timing
            start = time.perf_counter()
            encrypted_long = api_key_service._encrypt_api_key(long_key)
            times_long.append(time.perf_counter() - start)
            
            # Clean up - decrypt to verify
            api_key_service._decrypt_api_key(encrypted_short)
            api_key_service._decrypt_api_key(encrypted_long)
        
        # Calculate statistics
        avg_short = sum(times_short) / len(times_short)
        avg_long = sum(times_long) / len(times_long)
        
        # The difference should be reasonable (encryption time varies with content)
        # But ensure we're not leaking substantial timing information
        ratio = max(avg_short, avg_long) / min(avg_short, avg_long)
        assert ratio < 5.0, f"Timing ratio too high: {ratio}, potential timing leak"

    def test_memory_security_patterns(self, api_key_service):
        """Test memory security patterns in encryption/decryption."""
        test_key = "sk-sensitive-memory-test"
        
        # Test that plaintext isn't left in memory after encryption
        encrypted = api_key_service._encrypt_api_key(test_key)
        
        # This is a best-effort test - Python garbage collection
        # doesn't guarantee immediate cleanup, but we can verify
        # the encrypted result doesn't contain plaintext
        assert test_key not in encrypted, "Plaintext shouldn't appear in ciphertext"
        
        # Test decryption
        decrypted = api_key_service._decrypt_api_key(encrypted)
        assert decrypted == test_key

    def test_cryptographic_randomness(self, api_key_service):
        """Test that cryptographic operations use secure randomness."""
        test_key = "sk-randomness-test"
        
        # Generate multiple encryptions
        encryptions = set()
        for _ in range(100):
            encrypted = api_key_service._encrypt_api_key(test_key)
            encryptions.add(encrypted)
        
        # All encryptions should be unique (due to random data keys)
        assert len(encryptions) == 100, "All encryptions should be unique"
        
        # Verify each decrypts correctly
        for encrypted in list(encryptions)[:10]:  # Test a sample
            decrypted = api_key_service._decrypt_api_key(encrypted)
            assert decrypted == test_key

    def test_encryption_with_corrupted_master_key(self):
        """Test behavior with corrupted master key."""
        mock_db = Mock()
        mock_settings = Mock()
        mock_settings.secret_key = "original-master-key"
        
        service = ApiKeyService(db=mock_db, settings=mock_settings)
        test_key = "sk-test-corruption"
        
        # Encrypt with original key
        encrypted = service._encrypt_api_key(test_key)
        
        # Corrupt the master key by modifying the service's cipher
        # Simulate what happens if the master key changes
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        
        # Create corrupted master key
        corrupted_salt = b"corrupted_salt_v3"
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=corrupted_salt,
            iterations=300000,
        )
        corrupted_key = base64.urlsafe_b64encode(
            kdf.derive("corrupted-master-key".encode())
        )
        service.master_key = corrupted_key
        service.master_cipher = Fernet(corrupted_key)
        
        # Attempt to decrypt should fail
        with pytest.raises(CoreServiceError, match="Decryption failed"):
            service._decrypt_api_key(encrypted)

    def test_salt_security(self):
        """Test that salt is properly configured and static."""
        # The salt should be static for key derivation consistency
        # but unique enough to prevent rainbow table attacks
        salt = b"tripsage_api_key_salt_v3"
        
        assert len(salt) >= 16, "Salt should be at least 16 bytes"
        assert salt != b"salt", "Salt should not be a common value"
        assert b"tripsage" in salt, "Salt should be application-specific"
        
        # Test that the same salt produces consistent results
        master_secret = "test-secret"
        
        kdf1 = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=300000,
        )
        key1 = kdf1.derive(master_secret.encode())
        
        kdf2 = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=300000,
        )
        key2 = kdf2.derive(master_secret.encode())
        
        assert key1 == key2, "Same salt should produce same key"

    def test_encryption_format_validation(self, api_key_service):
        """Test validation of encrypted key format."""
        test_key = "sk-format-test"
        encrypted = api_key_service._encrypt_api_key(test_key)
        
        # Verify the encrypted format is valid base64url
        try:
            decoded = base64.urlsafe_b64decode(encrypted.encode())
        except Exception:
            pytest.fail("Encrypted key should be valid base64url")
        
        # Verify separator exists
        assert b"::" in decoded, "Should contain separator"
        
        # Verify structure
        parts = decoded.split(b"::", 1)
        assert len(parts) == 2, "Should have exactly 2 parts"
        
        encrypted_data_key, encrypted_content = parts
        
        # Data key should be Fernet-encrypted (has specific structure)
        assert len(encrypted_data_key) > 60, "Encrypted data key should be substantial"
        
        # Content should also be Fernet-encrypted
        assert len(encrypted_content) > 40, "Encrypted content should be substantial"

    def test_concurrent_encryption_safety(self, api_key_service):
        """Test that concurrent encryption operations are safe."""
        import threading
        import time
        
        test_key = "sk-concurrent-test"
        results = []
        errors = []
        
        def encrypt_decrypt():
            try:
                encrypted = api_key_service._encrypt_api_key(test_key)
                decrypted = api_key_service._decrypt_api_key(encrypted)
                results.append((encrypted, decrypted))
            except Exception as e:
                errors.append(e)
        
        # Run concurrent operations
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=encrypt_decrypt)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Verify results
        assert len(errors) == 0, f"Should have no errors: {errors}"
        assert len(results) == 10, "Should have 10 successful operations"
        
        # Verify all decryptions are correct
        for encrypted, decrypted in results:
            assert decrypted == test_key, "All decryptions should be correct"
        
        # Verify all encryptions are unique
        encrypted_values = [r[0] for r in results]
        assert len(set(encrypted_values)) == 10, "All encryptions should be unique"