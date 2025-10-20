"""Comprehensive unit tests for connection utilities.

Tests cover:
- Database URL parsing with various formats and edge cases
- Security validation and malformed URL handling
- Connection validation and health checks
- Retry logic with exponential backoff
- Circuit breaker functionality
- Supabase-specific URL formats
- Error handling and logging
"""

import asyncio
import logging
import time
from unittest.mock import AsyncMock, patch
from urllib.parse import quote_plus

import pytest
from pydantic import ValidationError

from tripsage_core.utils.connection_utils import (
    ConnectionCircuitBreaker,
    ConnectionCredentials,
    ConnectionState,
    DatabaseConnectionError,
    DatabaseConnectionValidator,
    DatabaseURLParser,
    DatabaseURLParsingError,
    DatabaseValidationError,
    ExponentialBackoffRetry,
    SecureDatabaseConnectionManager,
    parse_database_url,
    validate_database_connection,
)


class TestConnectionCredentials:
    """Test ConnectionCredentials model validation and methods."""

    def test_valid_credentials_creation(self):
        """Test creating valid connection credentials."""
        credentials = ConnectionCredentials(
            scheme="postgresql",
            username="testuser",
            password="testpass",
            hostname="localhost",
            port=5432,
            database="testdb",
            query_params={"sslmode": "require"},
        )

        assert credentials.scheme == "postgresql"
        assert credentials.username == "testuser"
        assert credentials.password == "testpass"
        assert credentials.hostname == "localhost"
        assert credentials.port == 5432
        assert credentials.database == "testdb"
        assert credentials.query_params == {"sslmode": "require"}

    def test_default_values(self):
        """Test default values for optional fields."""
        credentials = ConnectionCredentials(
            scheme="postgres", username="user", password="pass", hostname="host"
        )

        assert credentials.port == 5432
        assert credentials.database == "postgres"
        assert credentials.query_params == {}

    def test_invalid_port_validation(self):
        """Test port validation with invalid values."""
        with pytest.raises(ValidationError):
            ConnectionCredentials(
                scheme="postgresql",
                username="user",
                password="pass",
                hostname="host",
                port=70000,  # Invalid port
            )

        with pytest.raises(ValidationError):
            ConnectionCredentials(
                scheme="postgresql",
                username="user",
                password="pass",
                hostname="host",
                port=0,  # Invalid port
            )

    def test_to_connection_string(self):
        """Test connection string generation."""
        credentials = ConnectionCredentials(
            scheme="postgresql",
            username="user@domain",
            password="p@ss/w0rd#123",
            hostname="localhost",
            port=5432,
            database="mydb",
            query_params={"sslmode": "require", "connect_timeout": "30"},
        )

        conn_string = credentials.to_connection_string()

        # Verify encoded components
        assert "user%40domain" in conn_string  # @ encoded
        assert "p%40ss%2Fw0rd%23123" in conn_string  # Special chars encoded
        assert "sslmode=require" in conn_string
        assert "connect_timeout=30" in conn_string
        assert conn_string.startswith("postgresql://")

    def test_to_connection_string_masked(self):
        """Test connection string generation with masked password."""
        credentials = ConnectionCredentials(
            scheme="postgresql",
            username="user",
            password="secret",
            hostname="localhost",
        )

        masked_string = credentials.to_connection_string(mask_password=True)

        assert "***MASKED***" in masked_string
        assert "secret" not in masked_string

    def test_sanitized_for_logging(self):
        """Test sanitized connection string for logging."""
        credentials = ConnectionCredentials(
            scheme="postgresql",
            username="user",
            password="secret",
            hostname="localhost",
        )

        log_string = credentials.sanitized_for_logging()

        assert "***MASKED***" in log_string
        assert "secret" not in log_string


class TestDatabaseURLParser:
    """Test DatabaseURLParser functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = DatabaseURLParser()

    def test_parse_basic_postgresql_url(self):
        """Test parsing basic PostgreSQL URL."""
        url = "postgresql://user:pass@localhost:5432/mydb"
        credentials = self.parser.parse_url(url)

        assert credentials.scheme == "postgresql"
        assert credentials.username == "user"
        assert credentials.password == "pass"
        assert credentials.hostname == "localhost"
        assert credentials.port == 5432
        assert credentials.database == "mydb"

    def test_parse_postgres_scheme(self):
        """Test parsing with 'postgres' scheme."""
        url = "postgres://user:pass@localhost/mydb"
        credentials = self.parser.parse_url(url)

        assert credentials.scheme == "postgres"
        assert credentials.port == 5432  # Default port

    def test_parse_url_with_query_params(self):
        """Test parsing URL with query parameters."""
        url = "postgresql://user:pass@localhost/mydb?sslmode=require&connect_timeout=30"
        credentials = self.parser.parse_url(url)

        expected_params = {"sslmode": "require", "connect_timeout": "30"}
        assert credentials.query_params == expected_params

    def test_parse_url_with_encoded_credentials(self):
        """Test parsing URL with encoded credentials."""
        username = "user@domain.com"
        password = "p@ss/w0rd#123"
        encoded_username = quote_plus(username)
        encoded_password = quote_plus(password)

        url = f"postgresql://{encoded_username}:{encoded_password}@localhost/mydb"
        credentials = self.parser.parse_url(url)

        assert credentials.username == username
        assert credentials.password == password

    def test_parse_supabase_url_formats(self):
        """Test parsing various Supabase URL formats."""
        # Direct connection
        url1 = (
            "postgresql://postgres.abcdef:password@db.abcdef.supabase.co:5432/postgres"
        )
        credentials1 = self.parser.parse_url(url1)
        assert credentials1.hostname == "db.abcdef.supabase.co"
        assert credentials1.username == "postgres.abcdef"

        # Session pooler
        url2 = "postgresql://postgres.abcdef:password@aws-0-us-west-1.pooler.supabase.com:5432/postgres"
        credentials2 = self.parser.parse_url(url2)
        assert "pooler.supabase.com" in credentials2.hostname

        # Transaction pooler
        url3 = "postgresql://postgres.abcdef:password@aws-0-us-west-1.pooler.supabase.com:6543/postgres"
        credentials3 = self.parser.parse_url(url3)
        assert credentials3.port == 6543

    def test_parse_url_without_database_path(self):
        """Test parsing URL without database path."""
        url = "postgresql://user:pass@localhost:5432"
        credentials = self.parser.parse_url(url)

        assert credentials.database == "postgres"  # Default

    def test_parse_url_with_empty_database_path(self):
        """Test parsing URL with empty database path."""
        url = "postgresql://user:pass@localhost:5432/"
        credentials = self.parser.parse_url(url)

        assert credentials.database == "postgres"  # Default

    def test_invalid_scheme_error(self):
        """Test error handling for invalid schemes."""
        with pytest.raises(DatabaseURLParsingError, match="Invalid scheme"):
            self.parser.parse_url("mysql://user:pass@localhost/db")

        with pytest.raises(DatabaseURLParsingError, match="Invalid scheme"):
            self.parser.parse_url("http://user:pass@localhost/db")

    def test_missing_hostname_error(self):
        """Test error handling for missing hostname."""
        with pytest.raises(DatabaseURLParsingError, match="Hostname is required"):
            self.parser.parse_url("postgresql://user:pass@/db")

    def test_missing_username_error(self):
        """Test error handling for missing username."""
        with pytest.raises(DatabaseURLParsingError, match="Username is required"):
            self.parser.parse_url("postgresql://:pass@localhost/db")

    def test_missing_password_error(self):
        """Test error handling for missing password."""
        with pytest.raises(DatabaseURLParsingError, match="Password is required"):
            self.parser.parse_url("postgresql://user@localhost/db")

    def test_security_validation_empty_url(self):
        """Test security validation with empty URL."""
        with pytest.raises(DatabaseURLParsingError, match="non-empty string"):
            self.parser.parse_url("")

        with pytest.raises(DatabaseURLParsingError, match="non-empty string"):
            self.parser.parse_url(None)

    def test_security_validation_whitespace(self):
        """Test security validation with whitespace (CVE-2023-24329)."""
        with pytest.raises(
            DatabaseURLParsingError, match="leading/trailing whitespace"
        ):
            self.parser.parse_url("  postgresql://user:pass@localhost/db  ")

    def test_security_validation_control_characters(self):
        """Test security validation with control characters."""
        with pytest.raises(DatabaseURLParsingError, match="control characters"):
            self.parser.parse_url("postgresql://user:pass@localhost/db\x00")

    def test_security_validation_missing_scheme_separator(self):
        """Test security validation with missing scheme separator."""
        with pytest.raises(DatabaseURLParsingError, match="scheme separator"):
            self.parser.parse_url("postgresqluser:pass@localhost/db")


class TestConnectionCircuitBreaker:
    """Test ConnectionCircuitBreaker functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.circuit_breaker = ConnectionCircuitBreaker(
            failure_threshold=3,
            recovery_timeout=1.0,  # Short timeout for testing
        )

    @pytest.mark.asyncio
    async def test_circuit_breaker_closed_state(self):
        """Test circuit breaker in closed state."""

        async def successful_operation():
            return "success"

        result = await self.circuit_breaker.call(successful_operation)
        assert result == "success"
        assert self.circuit_breaker.state == ConnectionState.CLOSED
        assert self.circuit_breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_failure_counting(self):
        """Test circuit breaker failure counting."""

        async def failing_operation():
            raise Exception("Test failure")

        # First two failures should not open circuit
        for i in range(2):
            with pytest.raises(Exception, match="Test failure"):
                await self.circuit_breaker.call(failing_operation)
            assert self.circuit_breaker.state == ConnectionState.CLOSED
            assert self.circuit_breaker.failure_count == i + 1

    @pytest.mark.asyncio
    async def test_circuit_breaker_opening(self):
        """Test circuit breaker opening after threshold."""

        async def failing_operation():
            raise Exception("Test failure")

        # Trigger failures to open circuit
        for _ in range(3):
            with pytest.raises(Exception, match="Test failure"):
                await self.circuit_breaker.call(failing_operation)

        assert self.circuit_breaker.state == ConnectionState.OPEN

        # Subsequent calls should raise DatabaseConnectionError
        with pytest.raises(DatabaseConnectionError, match="Circuit breaker is OPEN"):
            await self.circuit_breaker.call(failing_operation)

    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_transition(self):
        """Test circuit breaker transitioning to half-open."""

        async def failing_operation():
            raise Exception("Test failure")

        # Open the circuit
        for _ in range(3):
            with pytest.raises(Exception, match="Test failure"):
                await self.circuit_breaker.call(failing_operation)

        assert self.circuit_breaker.state == ConnectionState.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(1.1)

        # Next call should transition to half-open
        with pytest.raises(Exception, match="Test failure"):
            await self.circuit_breaker.call(failing_operation)

        # Circuit should reopen after failure in half-open state
        assert self.circuit_breaker.state == ConnectionState.OPEN

    @pytest.mark.asyncio
    async def test_circuit_breaker_recovery(self):
        """Test circuit breaker recovery to closed state."""

        async def failing_operation():
            raise Exception("Test failure")

        async def successful_operation():
            return "success"

        # Open the circuit
        for _ in range(3):
            with pytest.raises(Exception, match="Test failure"):
                await self.circuit_breaker.call(failing_operation)

        # Wait for recovery timeout
        await asyncio.sleep(1.1)

        # Successful call should close the circuit
        result = await self.circuit_breaker.call(successful_operation)
        assert result == "success"
        assert self.circuit_breaker.state == ConnectionState.CLOSED
        assert self.circuit_breaker.failure_count == 0


class TestExponentialBackoffRetry:
    """Test ExponentialBackoffRetry functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.retry = ExponentialBackoffRetry(
            max_retries=3,
            base_delay=0.1,  # Short delays for testing
            max_delay=1.0,
            jitter=False,  # Disable jitter for predictable tests
        )

    def test_calculate_delay(self):
        """Test delay calculation."""
        assert self.retry.calculate_delay(0) == 0.1
        assert self.retry.calculate_delay(1) == 0.2
        assert self.retry.calculate_delay(2) == 0.4
        assert self.retry.calculate_delay(3) == 0.8
        assert self.retry.calculate_delay(10) == 1.0  # Capped at max_delay

    def test_calculate_delay_with_jitter(self):
        """Test delay calculation with jitter."""
        retry_with_jitter = ExponentialBackoffRetry(
            max_retries=3, base_delay=0.1, jitter=True
        )

        # With jitter, delay should be slightly higher
        delay = retry_with_jitter.calculate_delay(1)
        assert delay >= 0.2  # Base delay
        assert delay <= 0.22  # Base delay + 10% jitter

    @pytest.mark.asyncio
    async def test_successful_operation_no_retry(self):
        """Test successful operation without retries."""
        call_count = 0

        async def successful_operation():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await self.retry.execute_with_retry(successful_operation)
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_operation_succeeds_after_retries(self):
        """Test operation succeeding after retries."""
        call_count = 0

        async def flaky_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return "success"

        result = await self.retry.execute_with_retry(flaky_operation)
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_operation_fails_after_all_retries(self):
        """Test operation failing after all retries."""
        call_count = 0

        async def failing_operation():
            nonlocal call_count
            call_count += 1
            raise Exception("Persistent failure")

        with pytest.raises(Exception, match="Persistent failure"):
            await self.retry.execute_with_retry(failing_operation)

        assert call_count == 4  # Initial attempt + 3 retries


class TestDatabaseConnectionValidator:
    """Test DatabaseConnectionValidator functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = DatabaseConnectionValidator(timeout=5.0)
        self.valid_credentials = ConnectionCredentials(
            scheme="postgresql",
            username="testuser",
            password="testpass",
            hostname="localhost",
            port=5432,
            database="testdb",
        )

    @pytest.mark.asyncio
    async def test_validate_connection_success(self):
        """Test successful connection validation."""
        with patch("asyncpg.connect") as mock_connect:
            # Setup mock connection
            mock_conn = AsyncMock()
            # Health check, version, pgvector
            mock_conn.fetchval.side_effect = [1, "PostgreSQL 15.0", True]
            mock_connect.return_value = mock_conn

            result = await self.validator.validate_connection(self.valid_credentials)

            assert result is True
            mock_connect.assert_called_once()
            mock_conn.fetchval.assert_any_call("SELECT 1")
            mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_connection_timeout(self):
        """Test connection validation timeout."""
        with patch("asyncpg.connect") as mock_connect:
            # Simulate timeout
            mock_connect.side_effect = TimeoutError()

            with pytest.raises(DatabaseValidationError, match="timed out"):
                await self.validator.validate_connection(self.valid_credentials)

    @pytest.mark.asyncio
    async def test_validate_connection_failure(self):
        """Test connection validation failure."""
        with patch("asyncpg.connect") as mock_connect:
            # Simulate connection failure
            mock_connect.side_effect = Exception("Connection refused")

            with pytest.raises(
                DatabaseValidationError, match="Connection validation failed"
            ):
                await self.validator.validate_connection(self.valid_credentials)

    @pytest.mark.asyncio
    async def test_validate_connection_with_ssl_require(self):
        """Test connection validation with SSL requirement."""
        credentials_with_ssl = ConnectionCredentials(
            scheme="postgresql",
            username="testuser",
            password="testpass",
            hostname="localhost",
            port=5432,
            database="testdb",
            query_params={"sslmode": "require"},
        )

        with patch("asyncpg.connect") as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.fetchval.side_effect = [1, "PostgreSQL 15.0", True]
            mock_connect.return_value = mock_conn

            await self.validator.validate_connection(credentials_with_ssl)

            # Verify SSL was required
            mock_connect.assert_called_once()
            call_args = mock_connect.call_args
            assert call_args.kwargs["ssl"] == "require"


class TestSecureDatabaseConnectionManager:
    """Test SecureDatabaseConnectionManager functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = SecureDatabaseConnectionManager(
            max_retries=2, circuit_breaker_threshold=3, validation_timeout=5.0
        )

    @pytest.mark.asyncio
    async def test_parse_and_validate_url_success(self):
        """Test successful URL parsing and validation."""
        url = "postgresql://user:pass@localhost:5432/testdb"

        with patch("asyncpg.connect") as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.fetchval.side_effect = [1, "PostgreSQL 15.0", True]
            mock_connect.return_value = mock_conn

            credentials = await self.manager.parse_and_validate_url(url)

            assert credentials.hostname == "localhost"
            assert credentials.username == "user"
            assert credentials.password == "pass"

    @pytest.mark.asyncio
    async def test_parse_and_validate_url_parsing_error(self):
        """Test URL parsing error handling."""
        invalid_url = "invalid-url"

        with pytest.raises(DatabaseURLParsingError):
            await self.manager.parse_and_validate_url(invalid_url)

    @pytest.mark.asyncio
    async def test_get_validated_connection_success(self):
        """Test getting validated connection."""
        url = "postgresql://user:pass@localhost:5432/testdb"

        with patch("asyncpg.connect") as mock_connect:
            mock_conn = AsyncMock()
            # For validation: health check, version, pgvector
            mock_conn.fetchval.side_effect = [1, "PostgreSQL 15.0", True]
            mock_connect.return_value = mock_conn

            async with self.manager.get_validated_connection(url) as conn:
                assert conn is mock_conn

            # Verify connection was closed
            mock_conn.close.assert_called()

    @pytest.mark.asyncio
    async def test_get_validated_connection_failure(self):
        """Test connection failure handling."""
        url = "postgresql://user:pass@localhost:5432/testdb"

        with patch("asyncpg.connect") as mock_connect:
            mock_connect.side_effect = Exception("Connection failed")

            with pytest.raises(DatabaseValidationError):
                async with self.manager.get_validated_connection(url):
                    pass


class TestConvenienceFunctions:
    """Test convenience functions for backward compatibility."""

    @pytest.mark.asyncio
    async def test_parse_database_url_function(self):
        """Test parse_database_url convenience function."""
        url = "postgresql://user:pass@localhost:5432/testdb"
        credentials = await parse_database_url(url)

        assert credentials.hostname == "localhost"
        assert credentials.username == "user"
        assert credentials.password == "pass"

    @pytest.mark.asyncio
    async def test_validate_database_connection_function_success(self):
        """Test validate_database_connection convenience function - success."""
        url = "postgresql://user:pass@localhost:5432/testdb"

        with patch("asyncpg.connect") as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.fetchval.side_effect = [1, "PostgreSQL 15.0", True]
            mock_connect.return_value = mock_conn

            result = await validate_database_connection(url)
            assert result is True

    @pytest.mark.asyncio
    async def test_validate_database_connection_function_failure(self):
        """Test validate_database_connection convenience function - failure."""
        url = "invalid-url"

        result = await validate_database_connection(url)
        assert result is False


class TestEdgeCasesAndSecurity:
    """Test edge cases and security scenarios."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = DatabaseURLParser()

    def test_ipv6_hostname_parsing(self):
        """Test parsing URLs with IPv6 hostnames."""
        url = "postgresql://user:pass@[::1]:5432/testdb"
        credentials = self.parser.parse_url(url)

        assert credentials.hostname == "::1"
        assert credentials.port == 5432

    def test_complex_password_parsing(self):
        """Test parsing URLs with complex passwords."""
        complex_passwords = [
            "p@ssw0rd!#$%^&*()",
            "münchen_password",
            "密码123",
            "pássword_wîth_ãccénts",
        ]

        for password in complex_passwords:
            encoded_password = quote_plus(password)
            url = f"postgresql://user:{encoded_password}@localhost/db"
            credentials = self.parser.parse_url(url)
            assert credentials.password == password

    def test_url_with_fragment_ignored(self):
        """Test that URL fragments are ignored."""
        url = "postgresql://user:pass@localhost/db#fragment"
        credentials = self.parser.parse_url(url)

        # Fragment should be ignored
        assert credentials.database == "db"

    def test_empty_query_parameter_values(self):
        """Test handling of empty query parameter values."""
        url = "postgresql://user:pass@localhost/db?sslmode=&timeout=30"
        credentials = self.parser.parse_url(url)

        assert credentials.query_params["sslmode"] == ""
        assert credentials.query_params["timeout"] == "30"

    def test_query_parameter_without_value(self):
        """Test handling of query parameters without values."""
        url = "postgresql://user:pass@localhost/db?sslmode&timeout=30"
        credentials = self.parser.parse_url(url)

        assert credentials.query_params["sslmode"] == ""
        assert credentials.query_params["timeout"] == "30"

    def test_malformed_port_in_url(self):
        """Test handling of malformed port in URL."""
        # urlparse will handle this, but our validation should catch it
        url = "postgresql://user:pass@localhost:abc/db"

        # This should be caught by our hostname/port validation
        # The exact error depends on how urllib.parse handles it
        with pytest.raises(DatabaseURLParsingError):
            self.parser.parse_url(url)

    def test_extremely_long_url(self):
        """Test handling of extremely long URLs."""
        long_password = "a" * 10000
        encoded_password = quote_plus(long_password)
        url = f"postgresql://user:{encoded_password}@localhost/db"

        # Should handle long URLs gracefully
        credentials = self.parser.parse_url(url)
        assert credentials.password == long_password

    def test_sql_injection_attempt_in_database_name(self):
        """Test handling of potential SQL injection in database name."""
        malicious_db = "testdb'; DROP TABLE users; --"
        encoded_db = quote_plus(malicious_db)
        url = f"postgresql://user:pass@localhost:5432/{encoded_db}"

        credentials = self.parser.parse_url(url)
        # The malicious string should be safely stored as the database name
        assert credentials.database == malicious_db

    def test_unicode_domain_name(self):
        """Test handling of internationalized domain names."""
        # Most URL parsers handle IDN, but we should test edge cases
        url = "postgresql://user:pass@münchen.example.com/db"
        credentials = self.parser.parse_url(url)

        assert "münchen" in credentials.hostname


@pytest.fixture
def caplog_setup(caplog):
    """Set up logging capture for tests."""
    caplog.set_level(logging.DEBUG)
    return caplog


class TestLoggingAndMonitoring:
    """Test logging and monitoring functionality."""

    def test_parser_logging_success(self, caplog_setup):
        """Test successful parsing logs appropriate messages."""
        parser = DatabaseURLParser()
        url = "postgresql://user:pass@localhost:5432/testdb"

        parser.parse_url(url)

        # Check that success was logged
        assert "Successfully parsed database URL" in caplog_setup.text
        assert "localhost" in caplog_setup.text

    def test_parser_logging_failure(self, caplog_setup):
        """Test failed parsing logs appropriate error messages."""
        parser = DatabaseURLParser()

        with pytest.raises(DatabaseURLParsingError):
            parser.parse_url("invalid-url")

        # Check that error was logged
        assert "Failed to parse database URL" in caplog_setup.text

    def test_circuit_breaker_logging(self, caplog_setup):
        """Test circuit breaker logs state transitions."""
        circuit_breaker = ConnectionCircuitBreaker(failure_threshold=2)

        # Open circuit by causing failures
        async def failing_operation():
            raise Exception("Test failure")

        async def test_logging():
            for _ in range(2):
                with pytest.raises(Exception, match="Test failure"):
                    await circuit_breaker.call(failing_operation)

        asyncio.run(test_logging())

        # Check that circuit opening was logged
        assert "Circuit breaker opening" in caplog_setup.text

    def test_credential_sanitization_in_logs(self, caplog_setup):
        """Test that sensitive credentials are not logged."""
        credentials = ConnectionCredentials(
            scheme="postgresql",
            username="testuser",
            password="secretpassword",
            hostname="localhost",
        )

        # Any logging should use sanitized version
        log_string = credentials.sanitized_for_logging()

        assert "secretpassword" not in log_string
        assert "***MASKED***" in log_string


class TestPerformanceCharacteristics:
    """Test performance characteristics of connection utilities."""

    def test_parser_performance_with_large_urls(self):
        """Test parser performance with large URLs."""
        # Create a URL with many query parameters
        base_url = "postgresql://user:pass@localhost:5432/db"
        query_params = [f"param{i}=value{i}" for i in range(1000)]
        large_url = f"{base_url}?{'&'.join(query_params)}"

        parser = DatabaseURLParser()
        start_time = time.time()
        credentials = parser.parse_url(large_url)
        parse_time = time.time() - start_time

        # Should parse in reasonable time (less than 1 second)
        assert parse_time < 1.0
        assert len(credentials.query_params) == 1000

    @pytest.mark.asyncio
    async def test_retry_timing_accuracy(self):
        """Test that retry timing is reasonably accurate."""
        retry = ExponentialBackoffRetry(max_retries=2, base_delay=0.1, jitter=False)

        call_times = []

        async def failing_operation():
            call_times.append(time.time())
            raise Exception("Test failure")

        with pytest.raises(Exception, match="Test failure"):
            await retry.execute_with_retry(failing_operation)

        # Verify timing between calls
        assert len(call_times) == 3  # Initial + 2 retries

        # Check approximate delays (allowing for some variance)
        delay1 = call_times[1] - call_times[0]
        delay2 = call_times[2] - call_times[1]

        assert 0.08 <= delay1 <= 0.12  # ~0.1s ± 20ms
        assert 0.18 <= delay2 <= 0.22  # ~0.2s ± 20ms


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
