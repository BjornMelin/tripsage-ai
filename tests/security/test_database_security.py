"""Security tests for database connections after migration."""

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tripsage_core.utils.connection_utils import (
    ConnectionCircuitBreaker,
    ConnectionState,
    DatabaseConnectionError,
    DatabaseURLParser,
    DatabaseURLParsingError,
    DatabaseValidationError,
    ExponentialBackoffRetry,
    SecureDatabaseConnectionManager,
)
from tripsage_core.utils.url_converters import DatabaseURLConverter


class TestDatabaseSecurity:
    """Test database connection security measures after migration."""

    def test_no_credentials_in_logs(self, caplog):
        """Ensure credentials are never logged."""
        parser = DatabaseURLParser()

        with caplog.at_level(logging.DEBUG):
            credentials = parser.parse_url(
                "postgresql://user:supersecret123@host:5432/db?sslmode=require"
            )

            # Get sanitized version
            sanitized = credentials.sanitized_for_logging()

            # Check logs don't contain password
            log_text = caplog.text
            assert "supersecret123" not in log_text
            assert "***MASKED***" in sanitized
            assert "postgresql://user:***MASKED***@host:5432/db" in sanitized

    def test_sql_injection_prevention(self):
        """Test SQL injection attempts are caught during URL parsing."""
        parser = DatabaseURLParser()

        # Test various injection attempts
        injection_attempts = [
            "postgresql://user:pass@host:5432/db'; DROP TABLE users; --",
            "postgresql://user:pass@host:5432/db?sslmode=require'; DELETE FROM d; --",
            "postgresql://user'; DROP DATABASE prod; --:pass@host:5432/db",
        ]

        for malicious_url in injection_attempts:
            # Parser should encode dangerous characters
            credentials = parser.parse_url(malicious_url)

            # Check that dangerous SQL is not in parsed components
            assert "DROP" not in credentials.database
            assert "DELETE" not in credentials.database
            assert "DROP" not in credentials.username

            # Verify URL encoding happened
            conn_string = credentials.to_connection_string()
            assert "DROP" not in conn_string or "%20DROP%20" in conn_string

    def test_url_traversal_prevention(self):
        """Test path traversal attempts are prevented."""
        converter = DatabaseURLConverter()

        # Attempt path traversal in Supabase URLs
        malicious_urls = [
            "https://../../etc/passwd.supabase.co",
            "https://project/.../admin.supabase.co",
            "https://project%2F..%2Fetc.supabase.co",
            "https://../../../root.supabase.co",
        ]

        for url in malicious_urls:
            with pytest.raises(DatabaseURLParsingError):
                converter.extract_supabase_project_ref(url)

    def test_control_character_rejection(self):
        """Test URLs with control characters are rejected."""
        parser = DatabaseURLParser()

        # URLs with control characters
        bad_urls = [
            "postgresql://user:pass\x00@host/db",  # Null byte
            "postgresql://user:pass@host\x0d\x0a/db",  # CRLF
            "postgresql://\x1buser:pass@host/db",  # Escape
            "postgresql://user:pass@host/db\x7f",  # DEL
        ]

        for bad_url in bad_urls:
            with pytest.raises(DatabaseURLParsingError) as exc_info:
                parser.parse_url(bad_url)
            assert "control characters" in str(exc_info.value).lower()

    def test_whitespace_url_rejection(self):
        """Test URLs with leading/trailing whitespace are rejected."""
        parser = DatabaseURLParser()

        urls_with_whitespace = [
            " postgresql://user:pass@host/db",
            "postgresql://user:pass@host/db ",
            "\tpostgresql://user:pass@host/db",
            "postgresql://user:pass@host/db\n",
        ]

        for bad_url in urls_with_whitespace:
            with pytest.raises(DatabaseURLParsingError) as exc_info:
                parser.parse_url(bad_url)
            assert "whitespace" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_circuit_breaker_protection(self):
        """Test circuit breaker prevents cascade failures."""
        cb = ConnectionCircuitBreaker(failure_threshold=3, recovery_timeout=0.1)

        # Track call attempts
        call_count = 0

        async def failing_operation():
            nonlocal call_count
            call_count += 1
            raise DatabaseConnectionError("Connection failed")

        # Trigger failures to open circuit
        for _i in range(3):
            with pytest.raises(DatabaseConnectionError):
                await cb.call(failing_operation)

        assert cb.state == ConnectionState.OPEN
        assert cb.failure_count == 3

        # Circuit should reject calls when open
        with pytest.raises(DatabaseConnectionError) as exc_info:
            await cb.call(failing_operation)

        assert "Circuit breaker is OPEN" in str(exc_info.value)
        assert call_count == 3  # No additional calls made

        # Wait for recovery timeout
        await asyncio.sleep(0.15)

        # Circuit should transition to half-open
        async def success_operation():
            return "success"

        result = await cb.call(success_operation)
        assert result == "success"
        assert cb.state == ConnectionState.CLOSED
        assert cb.failure_count == 0

    @pytest.mark.asyncio
    async def test_retry_with_exponential_backoff(self):
        """Test exponential backoff retry logic."""
        retry = ExponentialBackoffRetry(
            max_retries=3,
            base_delay=0.01,  # Short delays for testing
            backoff_factor=2.0,
        )

        attempt_times = []
        attempt_count = 0

        async def failing_then_success():
            nonlocal attempt_count
            attempt_count += 1
            attempt_times.append(asyncio.get_event_loop().time())

            if attempt_count < 3:
                raise DatabaseConnectionError(f"Attempt {attempt_count} failed")
            return "success"

        result = await retry.execute_with_retry(failing_then_success)

        assert result == "success"
        assert attempt_count == 3

        # Verify exponential delays (with some tolerance for timing)
        if len(attempt_times) >= 3:
            delay1 = attempt_times[1] - attempt_times[0]
            delay2 = attempt_times[2] - attempt_times[1]

            # Second delay should be roughly 2x the first
            assert delay2 > delay1 * 1.5

    @pytest.mark.asyncio
    async def test_connection_validation_timeout(self):
        """Test connection validation enforces timeout."""
        from tripsage_core.utils.connection_utils import DatabaseConnectionValidator

        validator = DatabaseConnectionValidator(timeout=0.1)

        # Mock asyncpg to simulate slow connection
        with patch("tripsage_core.utils.connection_utils.asyncpg") as mock_asyncpg:

            async def slow_connect(**kwargs):
                await asyncio.sleep(1.0)  # Longer than timeout
                return MagicMock()

            mock_asyncpg.connect = slow_connect

            credentials = MagicMock()
            credentials.hostname = "test"
            credentials.port = 5432
            credentials.username = "user"
            credentials.password = "pass"
            credentials.database = "db"
            credentials.query_params = {}

            with pytest.raises(DatabaseValidationError) as exc_info:
                await validator.validate_connection(credentials)

            assert "timed out" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_secure_connection_manager_integration(self):
        """Test SecureDatabaseConnectionManager integrates all security features."""
        manager = SecureDatabaseConnectionManager(
            max_retries=2,
            circuit_breaker_threshold=3,
            validation_timeout=5.0,
        )

        # Test with invalid URL
        with pytest.raises(DatabaseURLParsingError):
            await manager.parse_and_validate_url("not-a-valid-url")

        # Test with malicious URL
        with pytest.raises(DatabaseURLParsingError):
            await manager.parse_and_validate_url(
                "postgresql://user:pass@host/db'; DROP TABLE users; --"
            )

        # Test credential masking in parsed URLs
        with patch.object(manager.validator, "validate_connection") as mock_validate:
            mock_validate.return_value = True

            credentials = await manager.parse_and_validate_url(
                "postgresql://user:secret123@host:5432/db"
            )

            sanitized = credentials.sanitized_for_logging()
            assert "secret123" not in sanitized
            assert "***MASKED***" in sanitized

    def test_ssl_mode_enforcement(self):
        """Test SSL mode is enforced in connections."""
        converter = DatabaseURLConverter()

        # Convert Supabase URL
        postgres_url = converter.supabase_to_postgres(
            "https://test.supabase.co", "test-password", sslmode="require"
        )

        assert "sslmode=require" in postgres_url

        # Parse and verify SSL in query params
        parser = DatabaseURLParser()
        credentials = parser.parse_url(postgres_url)

        assert credentials.query_params.get("sslmode") == "require"

        # Verify SSL is preserved in connection string
        conn_string = credentials.to_connection_string()
        assert "sslmode=require" in conn_string

    def test_password_special_character_handling(self):
        """Test passwords with special characters are properly encoded."""
        parser = DatabaseURLParser()

        # Password with special characters
        special_passwords = [
            "pass@word!",
            "p@ss#w0rd$",
            "pass%word&123",
            "p@ss=w0rd+test",
            "pass word with spaces",
            "påss∑ørd",  # Unicode
        ]

        for password in special_passwords:
            # Build URL with special password
            from urllib.parse import quote_plus

            encoded_pass = quote_plus(password)
            url = f"postgresql://user:{encoded_pass}@host:5432/db"

            # Parse URL
            credentials = parser.parse_url(url)

            # Verify password was decoded correctly
            assert credentials.password == password

            # Verify connection string re-encodes properly
            conn_string = credentials.to_connection_string()
            assert "postgresql://user:" in conn_string
            assert "@host:5432/db" in conn_string

            # Parse the regenerated URL to verify round-trip
            credentials2 = parser.parse_url(conn_string)
            assert credentials2.password == password

    @pytest.mark.asyncio
    async def test_connection_context_manager_security(self):
        """Test secure connection context manager."""
        manager = SecureDatabaseConnectionManager()

        with patch("tripsage_core.utils.connection_utils.asyncpg") as mock_asyncpg:
            # Mock connection
            mock_conn = AsyncMock()
            mock_asyncpg.connect = AsyncMock(return_value=mock_conn)

            # Mock validation
            with patch.object(manager, "parse_and_validate_url") as mock_validate:
                mock_creds = MagicMock()
                mock_creds.hostname = "host"
                mock_creds.port = 5432
                mock_creds.username = "user"
                mock_creds.password = "pass"
                mock_creds.database = "db"
                mock_creds.query_params = {"sslmode": "require"}
                mock_validate.return_value = mock_creds

                # Use connection
                url = "postgresql://user:pass@host:5432/db?sslmode=require"
                async with manager.get_validated_connection(url) as conn:
                    assert conn == mock_conn

                # Verify connection was validated
                mock_validate.assert_called_once_with(url)

                # Verify SSL mode was used
                mock_asyncpg.connect.assert_called_once()
                call_kwargs = mock_asyncpg.connect.call_args[1]
                assert call_kwargs["ssl"] == "require"

                # Verify connection was closed
                mock_conn.close.assert_called_once()
