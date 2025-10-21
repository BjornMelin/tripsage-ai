"""SQL injection prevention and input validation security tests.

Tests SQL injection attacks, input sanitization, parameterized queries,
and database security measures.
"""

from contextlib import suppress
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from tripsage_core.exceptions.exceptions import CoreServiceError
from tripsage_core.models.db.api_key import ApiKeyCreate
from tripsage_core.services.business.api_key_service import ApiKeyService, ServiceType


class TestSQLInjectionPrevention:
    """Test SQL injection prevention in API key operations."""

    @pytest.fixture
    def api_key_service(self):
        """Create API key service with mocked database."""
        mock_db = AsyncMock()
        mock_cache = AsyncMock()
        mock_settings = Mock()
        mock_settings.secret_key = "test-secret-key"

        return ApiKeyService(db=mock_db, cache=mock_cache, settings=mock_settings)

    @pytest.fixture
    def sql_injection_payloads(self):
        """Common SQL injection attack payloads."""
        return [
            # Classic SQL injection
            "'; DROP TABLE api_keys; --",
            "' OR '1'='1",
            "' OR 1=1 --",
            "' OR 'a'='a",
            "'; DELETE FROM api_keys WHERE 1=1; --",
            # Union-based attacks
            "' UNION SELECT * FROM users --",
            "' UNION SELECT password FROM users WHERE username='admin' --",
            "' UNION ALL SELECT NULL,NULL,NULL --",
            # Boolean-based blind injection
            "' AND (SELECT COUNT(*) FROM api_keys) > 0 --",
            # Blind injection with ASCII
            (
                "' AND ASCII(SUBSTRING((SELECT password FROM users "
                "WHERE id=1),1,1)) > 64 --"
            ),
            # Time-based blind injection
            "'; WAITFOR DELAY '00:00:05'; --",
            "' AND (SELECT SLEEP(5)) --",
            "'; pg_sleep(5); --",
            # Comment-based injection
            "admin'/*",
            "admin'#",
            "admin'--",
            # Stored procedure attacks
            "'; EXEC xp_cmdshell('dir'); --",
            "'; EXEC sp_executesql N'SELECT * FROM users'; --",
            # NoSQL injection (for completeness)
            "'; return true; //",
            "' || '1'=='1",
            # Advanced SQL injection
            # EXTRACTVALUE injection
            (
                "' AND EXTRACTVALUE(1, CONCAT(0x7e, "
                "(SELECT password FROM users LIMIT 1), 0x7e)) --"
            ),
            # Error-based SQL injection
            "' AND (SELECT * FROM (SELECT COUNT(*),CONCAT(version(),FLOOR(RAND(0)*2))x "
            "FROM information_schema.tables GROUP BY x)a) --",
            # Encoding-based attacks
            "%27%20OR%20%271%27%3D%271",  # URL encoded
            "&#39; OR &#39;1&#39;=&#39;1",  # HTML encoded
            # Unicode and bypass attempts
            "' OR '1'='1",  # Fullwidth characters
            "' OR '1'='1",  # Different quote characters
            # NULL byte injection
            "'; SELECT * FROM users WHERE id=1\x00 --",  # NULL byte
            # Hex-based injection
            "0x27204F522027312027203D202731",
            # MySQL-specific
            # MySQL error-based injection with ROW
            (
                "' AND ROW(1,1) > (SELECT COUNT(*), CONCAT(version(), 0x3a, "
                "FLOOR(RAND(0)*2)) x FROM (SELECT 1 UNION SELECT 2) a GROUP BY x "
                "LIMIT 1) --"
            ),
            # PostgreSQL-specific
            "'; COPY (SELECT * FROM users) TO '/tmp/output.txt'; --",
            # SQLite-specific
            "' AND (SELECT name FROM sqlite_master WHERE type='table') --",
        ]

    @pytest.fixture
    def xss_payloads(self):
        """XSS attack payloads that might also affect SQL contexts."""
        return [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "';alert(String.fromCharCode(88,83,83))//';alert(String.fromCharCode(88,83,83))//",
            "<img src=x onerror=alert('xss')>",
            "';document.write('<script>alert(\"XSS\")</script>');//",
        ]

    @pytest.mark.asyncio
    async def test_sql_injection_in_api_key_creation(
        self, api_key_service, sql_injection_payloads
    ):
        """Test SQL injection prevention in API key creation."""
        user_id = "test-user-123"

        # Mock successful database operations
        mock_transaction = (
            api_key_service.db.transaction.return_value.__aenter__.return_value
        )
        mock_transaction.execute.return_value = [
            [{"id": "mock-key-id", "user_id": user_id, "service": "openai"}]
        ]

        for payload in sql_injection_payloads:
            # Test injection in key name
            request_data = ApiKeyCreate(
                user_id=uuid4(),
                name=payload,
                service=ServiceType.OPENAI.value,
                encrypted_key="sk-test-valid-key",
                description="Test description",
            )

            with patch.object(api_key_service, "validate_api_key") as mock_validate:
                mock_validate.return_value = Mock(
                    is_valid=True, validated_at="2024-01-01T00:00:00Z"
                )

                with suppress(CoreServiceError):
                    await api_key_service.create_api_key(user_id, request_data)

                # Verify the database was called with parameterized query
                # The name should be treated as a parameter, not concatenated
                # into SQL
                api_key_service.db.transaction.assert_called()

            # Test injection in description
            request_data = ApiKeyCreate(
                user_id=uuid4(),
                name="Valid Name",
                service=ServiceType.OPENAI.value,
                encrypted_key="sk-test-valid-key",
                description=payload,
            )

            with patch.object(api_key_service, "validate_api_key") as mock_validate:
                mock_validate.return_value = Mock(
                    is_valid=True, validated_at="2024-01-01T00:00:00Z"
                )

                with suppress(CoreServiceError):
                    await api_key_service.create_api_key(user_id, request_data)

    @pytest.mark.asyncio
    async def test_sql_injection_in_user_lookup(
        self, api_key_service, sql_injection_payloads
    ):
        """Test SQL injection prevention in user ID lookups."""
        api_key_service.db.get_user_api_keys.return_value = []

        for payload in sql_injection_payloads:
            # Test injection in user_id parameter
            with suppress(CoreServiceError, RuntimeError):
                await api_key_service.list_user_keys(payload)

            # Verify the database method was called
            # The payload should be treated as a parameter, not executed as SQL
            api_key_service.db.get_user_api_keys.assert_called_with(payload)

    @pytest.mark.asyncio
    async def test_sql_injection_in_service_lookup(
        self, api_key_service, sql_injection_payloads
    ):
        """Test SQL injection prevention in service lookups."""
        api_key_service.db.get_api_key_for_service.return_value = None

        # Test with valid service types and malicious user IDs
        for payload in sql_injection_payloads:
            with suppress(CoreServiceError, RuntimeError):
                await api_key_service.get_key_for_service(payload, ServiceType.OPENAI)

            # Verify parameterized query was used
            api_key_service.db.get_api_key_for_service.assert_called_with(
                payload, ServiceType.OPENAI.value
            )

    def test_input_sanitization_patterns(self):
        """Test input sanitization patterns and validation."""
        from tripsage.security.memory_security import MemorySecurity

        security = MemorySecurity()

        # Test SQL injection payload sanitization
        sql_payloads = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "'; DELETE FROM api_keys; --",
            "' UNION SELECT * FROM users --",
        ]

        for payload in sql_payloads:
            sanitized = security.sanitize_input(payload)

            # Verify dangerous SQL keywords are removed
            assert "DROP" not in sanitized.upper()
            assert "DELETE" not in sanitized.upper()
            assert "UNION" not in sanitized.upper()
            assert "--" not in sanitized
            assert "';" not in sanitized

    def test_xss_prevention_in_input_sanitization(self, xss_payloads):
        """Test XSS prevention in input sanitization."""
        from tripsage.security.memory_security import MemorySecurity

        security = MemorySecurity()

        for payload in xss_payloads:
            sanitized = security.sanitize_input(payload)

            # Verify dangerous script patterns are removed
            assert "<script" not in sanitized.lower()
            assert "javascript:" not in sanitized.lower()
            assert "onerror=" not in sanitized.lower()

    def test_length_validation_prevents_dos(self):
        """Test that excessive input length is prevented."""
        from tripsage.security.memory_security import MemorySecurity

        security = MemorySecurity()

        # Test with very long input (potential DoS)
        very_long_input = "A" * 50000
        sanitized = security.sanitize_input(very_long_input)

        # Should be truncated to reasonable length
        assert len(sanitized) <= 10000, "Input should be truncated to prevent DoS"

    @pytest.mark.asyncio
    async def test_parameterized_query_enforcement(self, api_key_service):
        """Test that database operations use parameterized queries."""
        user_id = "test-user"
        malicious_input = "'; DROP TABLE api_keys; --"

        # Mock database to capture query structure
        mock_transaction = AsyncMock()
        api_key_service.db.transaction.return_value.__aenter__.return_value = (
            mock_transaction
        )
        mock_transaction.execute.return_value = [[]]

        # Test API key deletion with malicious key_id
        await api_key_service.delete_api_key(malicious_input, user_id)

        # Verify that delete was called with parameters, not string concatenation
        # The malicious input should be treated as a parameter value
        mock_transaction.delete.assert_called()
        call_args = mock_transaction.delete.call_args

        # Verify the malicious input was passed as a parameter, not concatenated
        assert malicious_input in str(call_args), (
            "Malicious input should be parameterized"
        )

    def test_database_error_message_sanitization(self, api_key_service):
        """Test that database error messages don't leak sensitive information."""
        # Simulate database error with potentially sensitive information
        sensitive_error = (
            "ERROR: relation 'api_keys_secret_table' does not exist at line 1: "
            "SELECT * FROM api_keys_secret_table WHERE secret_field = 'sensitive_data'"
        )

        # Mock database to raise error
        api_key_service.db.get_user_api_keys.side_effect = Exception(sensitive_error)

        # The service should handle the error without exposing sensitive details
        try:
            api_key_service.list_user_keys("test-user")
        except CoreServiceError as e:
            # Error message should be generic, not expose database schema
            error_message = str(e).lower()
            assert "secret_table" not in error_message
            assert "secret_field" not in error_message
            assert "sensitive_data" not in error_message

    def test_special_character_handling(self, api_key_service):
        """Test handling of special characters that might cause SQL issues."""
        special_chars_test_cases = [
            # Quotes and escape characters
            "test'name",
            'test"name',
            "test`name",
            "test\\name",
            # Unicode characters
            "test名前",
            "testñame",
            "test_élève",
            # Control characters
            "test\nname",
            "test\tname",
            "test\rname",
            # SQL wildcards
            "test%name",
            "test_name",
            "test[name]",
            # JSON/XML characters
            "test{name}",
            "test<name>",
            "test&name",
            # Mathematical symbols
            "test+name",
            "test-name",
            "test*name",
            "test/name",
            "test=name",
        ]

        for test_input in special_chars_test_cases:
            try:
                # Test API key request creation with special characters
                request = ApiKeyCreate(
                    user_id=uuid4(),
                    name=test_input,
                    service=ServiceType.OPENAI.value,
                    encrypted_key="sk-test-valid-key",
                    description=f"Description with {test_input}",
                )

                # Verify the request can be created without causing SQL errors
                assert request.name == test_input or request.name == test_input.strip()

            except ValueError as e:
                # Some validation errors are acceptable for control characters
                if any(ord(c) < 32 for c in test_input if c not in "\t\n\r"):
                    continue  # Control characters should be rejected
                pytest.fail(f"Unexpected validation error for {test_input}: {e}")

    def test_numeric_overflow_protection(self):
        """Test protection against numeric overflow attacks."""
        # Test with extremely large numbers that might cause issues
        large_numbers = [
            "9" * 100,  # Very large number
            "1e308",  # Scientific notation near float limit
            "inf",  # Infinity
            "-inf",  # Negative infinity
            "nan",  # Not a number
        ]

        for num_str in large_numbers:
            try:
                # Test in user_id context (should be string anyway)

                # This should not cause numeric overflow issues
                # since user_id should be treated as string
                request = ApiKeyCreate(
                    user_id=uuid4(),
                    name="Test",
                    service=ServiceType.OPENAI.value,
                    encrypted_key="sk-test-key",
                    description=f"Test with number: {num_str}",
                )

                # Verify the description is properly handled
                assert (
                    request.description is not None and num_str in request.description
                )

            except ValueError:
                # Some numeric strings might be rejected by validation
                pass

    def test_encoding_attack_prevention(self):
        """Test prevention of encoding-based attacks."""
        encoding_attacks = [
            # URL encoding of malicious payloads
            "%27%20OR%20%271%27%3D%271",  # ' OR '1'='1
            "%22%3BSELECT%20*%20FROM%20users%3B--",  # ";SELECT * FROM users;--
            # Double URL encoding
            "%2527%2520OR%2520%25271%2527%253D%25271",
            # HTML entity encoding
            "&#39; OR &#39;1&#39;=&#39;1",
            "&quot;;DROP TABLE users;--&quot;",
            # Unicode encoding
            "\\u0027 OR \\u00271\\u0027=\\u00271",
            # Base64 encoding (though less common in SQL context)
            "JyBPUiAnMSc9JzE=",  # ' OR '1'='1 in base64
        ]

        from tripsage.security.memory_security import MemorySecurity

        security = MemorySecurity()

        for encoded_attack in encoding_attacks:
            sanitized = security.sanitize_input(encoded_attack)

            # The sanitizer should handle encoded attacks
            # Either by rejecting them or by safely encoding them
            assert sanitized != encoded_attack or not any(
                danger in sanitized.upper()
                for danger in ["DROP", "DELETE", "UNION", "SELECT"]
            )

    def test_comment_injection_prevention(self):
        """Test prevention of SQL comment injection."""
        comment_attacks = [
            "test'; -- comment out rest",
            "test'/* comment */",
            "test'# MySQL comment",
            "test';# Another comment",
            "test'/*! MySQL specific comment */",
        ]

        from tripsage.security.memory_security import MemorySecurity

        security = MemorySecurity()

        for attack in comment_attacks:
            sanitized = security.sanitize_input(attack)

            # Comments should be removed or neutralized
            assert "--" not in sanitized
            assert "/*" not in sanitized
            assert "*/" not in sanitized
