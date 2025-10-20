"""Final-only unit tests for connection utilities (parser + credentials)."""

import logging
import time
from urllib.parse import quote_plus

import pytest
from pydantic import ValidationError

from tripsage_core.utils.connection_utils import (
    ConnectionCredentials,
    DatabaseURLParser,
    DatabaseURLParsingError,
)


class TestConnectionCredentials:
    """Test ConnectionCredentials model and helpers."""

    def test_valid_credentials_creation(self):
        """Create valid credentials and verify fields."""
        creds = ConnectionCredentials(
            scheme="postgresql",
            username="testuser",
            password="testpass",
            hostname="localhost",
            port=5432,
            database="testdb",
            query_params={"sslmode": "require"},
        )
        assert creds.scheme == "postgresql"
        assert creds.username == "testuser"
        assert creds.password == "testpass"
        assert creds.hostname == "localhost"
        assert creds.port == 5432
        assert creds.database == "testdb"
        assert creds.query_params == {"sslmode": "require"}

    def test_default_values(self):
        """Verify default port, database, and query_params."""
        creds = ConnectionCredentials(
            scheme="postgres", username="user", password="pass", hostname="host"
        )
        assert creds.port == 5432
        assert creds.database == "postgres"
        assert creds.query_params == {}

    def test_invalid_port_validation(self):
        """Reject out-of-range or zero port values."""
        with pytest.raises(ValidationError):
            ConnectionCredentials(
                scheme="postgresql",
                username="user",
                password="pass",
                hostname="host",
                port=70000,
            )
        with pytest.raises(ValidationError):
            ConnectionCredentials(
                scheme="postgresql",
                username="user",
                password="pass",
                hostname="host",
                port=0,
            )

    def test_to_connection_string(self):
        """Build a connection string with masking and proper encoding."""
        creds = ConnectionCredentials(
            scheme="postgresql",
            username="user@domain",
            password="p@ss/w0rd#123",
            hostname="localhost",
            port=5432,
            database="mydb",
            query_params={"sslmode": "require", "connect_timeout": "30"},
        )
        conn = creds.to_connection_string()
        assert conn.startswith("postgresql://")
        assert "user%40domain" in conn
        assert "p%40ss%2Fw0rd%23123" in conn
        assert "sslmode=require" in conn
        assert "connect_timeout=30" in conn

    def test_masked_and_sanitized(self):
        """Ensure passwords are masked in outputs."""
        creds = ConnectionCredentials(
            scheme="postgresql",
            username="user",
            password="secret",
            hostname="localhost",
        )
        masked = creds.to_connection_string(mask_password=True)
        assert "***MASKED***" in masked and "secret" not in masked
        safe = creds.sanitized_for_logging()
        assert "***MASKED***" in safe and "secret" not in safe


class TestDatabaseURLParser:
    """Test DatabaseURLParser functionality and validation."""

    def setup_method(self):
        """Create a fresh parser for each test."""
        self.parser = DatabaseURLParser()

    def test_parse_basic_postgresql_url(self):
        """Parse a canonical PostgreSQL URL with all components."""
        url = "postgresql://user:pass@localhost:5432/mydb"
        c = self.parser.parse_url(url)
        assert c.scheme == "postgresql"
        assert c.username == "user"
        assert c.password == "pass"
        assert c.hostname == "localhost"
        assert c.port == 5432
        assert c.database == "mydb"

    def test_parse_postgres_scheme(self):
        """Accept the postgres scheme alias and default port 5432."""
        url = "postgres://user:pass@localhost/mydb"
        c = self.parser.parse_url(url)
        assert c.scheme == "postgres"
        assert c.port == 5432

    def test_parse_url_with_query_params(self):
        """Extract query parameters as a dict of strings."""
        url = "postgresql://user:pass@localhost/mydb?sslmode=require&connect_timeout=30"
        c = self.parser.parse_url(url)
        assert c.query_params == {"sslmode": "require", "connect_timeout": "30"}

    def test_parse_url_with_encoded_credentials(self):
        """Decode percent-encoded username and password values."""
        username = "user@domain.com"
        password = "p@ss/w0rd#123"
        encoded_username = quote_plus(username)
        encoded_password = quote_plus(password)
        url = f"postgresql://{encoded_username}:{encoded_password}@localhost/mydb"
        c = self.parser.parse_url(url)
        assert c.username == username
        assert c.password == password

    def test_security_validation_empty_and_whitespace(self):
        """Reject empty, None, or whitespace-only URLs."""
        with pytest.raises(DatabaseURLParsingError):
            self.parser.parse_url("")
        with pytest.raises(DatabaseURLParsingError):
            self.parser.parse_url(None)  # type: ignore
        with pytest.raises(DatabaseURLParsingError):
            self.parser.parse_url("  postgresql://user:pass@localhost/db  ")

    def test_security_validation_control_characters(self):
        """Reject URLs containing NUL or control characters."""
        with pytest.raises(DatabaseURLParsingError):
            self.parser.parse_url("postgresql://user:pass@localhost/db\x00")

    def test_security_validation_missing_scheme_separator(self):
        """Reject URLs missing the scheme separator."""
        with pytest.raises(DatabaseURLParsingError):
            self.parser.parse_url("postgresqluser:pass@localhost/db")

    def test_missing_components(self):
        """Reject URLs missing username, password, or host."""
        with pytest.raises(DatabaseURLParsingError):
            self.parser.parse_url("postgresql://:pass@localhost/db")  # no username
        with pytest.raises(DatabaseURLParsingError):
            self.parser.parse_url("postgresql://user@localhost/db")  # no password
        with pytest.raises(DatabaseURLParsingError):
            self.parser.parse_url("postgresql://user:pass@/db")  # no host

    def test_ipv6_hostname_parsing(self):
        """Parse IPv6 hostnames in bracket notation."""
        url = "postgresql://user:pass@[::1]:5432/testdb"
        c = self.parser.parse_url(url)
        assert c.hostname == "::1"
        assert c.port == 5432

    def test_extremely_long_url(self):
        """Handle very long but valid password segments."""
        long_password = "a" * 10000
        encoded_password = quote_plus(long_password)
        url = f"postgresql://user:{encoded_password}@localhost/db"
        c = self.parser.parse_url(url)
        assert c.password == long_password

    def test_sql_injection_like_database_name(self):
        """Treat suspicious database names as plain strings."""
        malicious_db = "testdb'; DROP TABLE users; --"
        encoded_db = quote_plus(malicious_db)
        url = f"postgresql://user:pass@localhost:5432/{encoded_db}"
        c = self.parser.parse_url(url)
        assert c.database == malicious_db


@pytest.fixture
def caplog_setup(caplog):
    """Configure caplog at DEBUG for log assertions."""
    caplog.set_level(logging.DEBUG)
    return caplog


class TestLoggingAndPerformance:
    """Logging and performance characteristics."""

    def test_parser_debug_logging_contains_hostname(self, caplog_setup):
        """Emit hostname in debugging output when parsing URLs."""
        parser = DatabaseURLParser()
        url = "postgresql://user:pass@localhost:5432/testdb"
        parser.parse_url(url)
        assert "host=localhost" in caplog_setup.text or "localhost" in caplog_setup.text

    def test_large_url_parsing_performance(self):
        """Parse 1000-query-param URL within 1s and collect params."""
        base_url = "postgresql://user:pass@localhost:5432/db"
        query_params = [f"param{i}=value{i}" for i in range(1000)]
        large_url = f"{base_url}?{'&'.join(query_params)}"
        parser = DatabaseURLParser()
        start_time = time.time()
        c = parser.parse_url(large_url)
        parse_time = time.time() - start_time
        assert parse_time < 1.0
        assert len(c.query_params) == 1000
