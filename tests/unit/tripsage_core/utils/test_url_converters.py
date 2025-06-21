"""
Unit tests for database URL conversion utilities.

Tests the conversion between Supabase HTTPS URLs and PostgreSQL connection
strings with comprehensive edge cases and security validation.
"""

import pytest

from tripsage_core.utils.connection_utils import DatabaseURLParsingError
from tripsage_core.utils.url_converters import (
    DatabaseURLConverter,
    DatabaseURLDetector,
    convert_supabase_to_postgres,
    detect_database_url_type,
)


class TestDatabaseURLConverter:
    """Test database URL converter functionality."""

    @pytest.fixture
    def converter(self):
        """Create converter instance."""
        return DatabaseURLConverter()

    def test_is_supabase_url_valid(self, converter):
        """Test Supabase URL detection with valid URLs."""
        valid_urls = [
            "https://abcdefghijklmnop.supabase.co",
            "https://test-project-123.supabase.com",
            "https://my-app.supabase.co/",
            "https://prod-db-2024.supabase.com/",
        ]

        for url in valid_urls:
            assert converter.is_supabase_url(url) is True

    def test_is_supabase_url_invalid(self, converter):
        """Test Supabase URL detection with invalid URLs."""
        invalid_urls = [
            "http://project.supabase.co",  # Not HTTPS
            "https://supabase.co",  # No project ref
            "https://project.supabase.io",  # Wrong domain
            "https://project.notsupabase.co",  # Wrong domain
            "postgresql://user:pass@host:5432/db",  # PostgreSQL URL
            "https://example.com",  # Not Supabase
            "",  # Empty
        ]

        for url in invalid_urls:
            assert converter.is_supabase_url(url) is False

    def test_is_postgres_url_valid(self, converter):
        """Test PostgreSQL URL detection with valid URLs."""
        valid_urls = [
            "postgresql://user:pass@host:5432/db",
            "postgres://user:pass@host:5432/db",
            "postgresql://user:pass@host/db",
            "postgres://user:pass@host/",
        ]

        for url in valid_urls:
            assert converter.is_postgres_url(url) is True

    def test_is_postgres_url_invalid(self, converter):
        """Test PostgreSQL URL detection with invalid URLs."""
        invalid_urls = [
            "https://project.supabase.co",
            "mysql://user:pass@host/db",
            "mongodb://user:pass@host/db",
            "",
        ]

        for url in invalid_urls:
            assert converter.is_postgres_url(url) is False

    def test_extract_supabase_project_ref(self, converter):
        """Test extraction of project reference from Supabase URL."""
        test_cases = [
            ("https://myproject.supabase.co", ("myproject", "supabase.co")),
            ("https://test-123.supabase.com", ("test-123", "supabase.com")),
            ("https://prod-db-2024.supabase.co/", ("prod-db-2024", "supabase.co")),
        ]

        for url, expected in test_cases:
            project_ref, domain = converter.extract_supabase_project_ref(url)
            assert (project_ref, domain) == expected

    def test_extract_supabase_project_ref_invalid(self, converter):
        """Test extraction with invalid Supabase URLs."""
        invalid_urls = [
            "https://supabase.co",
            "http://project.supabase.co",
            "https://project.example.com",
            "postgresql://user:pass@host/db",
        ]

        for url in invalid_urls:
            with pytest.raises(DatabaseURLParsingError):
                converter.extract_supabase_project_ref(url)

    def test_supabase_to_postgres_basic(self, converter):
        """Test basic Supabase to PostgreSQL conversion."""
        result = converter.supabase_to_postgres("https://myproject.supabase.co", "test-service-key")

        expected = "postgresql://postgres:test-service-key@myproject.db.supabase.co:5432/postgres?sslmode=require"
        assert result == expected

    def test_supabase_to_postgres_with_pooler(self, converter):
        """Test conversion with connection pooler."""
        result = converter.supabase_to_postgres("https://myproject.supabase.co", "test-service-key", use_pooler=True)

        expected = "postgresql://postgres:test-service-key@myproject.db.supabase.co:6543/postgres?sslmode=require"
        assert result == expected

    def test_supabase_to_postgres_custom_params(self, converter):
        """Test conversion with custom parameters."""
        result = converter.supabase_to_postgres(
            "https://myproject.supabase.com",
            "test-key",
            username="custom_user",
            database="custom_db",
            sslmode="prefer",
        )

        expected = "postgresql://custom_user:test-key@myproject.db.supabase.com:5432/custom_db?sslmode=prefer"
        assert result == expected

    def test_supabase_to_postgres_special_chars(self, converter):
        """Test conversion with special characters in password."""
        result = converter.supabase_to_postgres("https://myproject.supabase.co", "p@ss!word#123")

        # Password should be URL encoded
        assert "p%40ss%21word%23123" in result

    def test_postgres_to_supabase_valid(self, converter):
        """Test extracting Supabase info from PostgreSQL URL."""
        postgres_url = "postgresql://postgres:key@myproject.db.supabase.co:5432/postgres"

        supabase_url, project_ref = converter.postgres_to_supabase(postgres_url)

        assert supabase_url == "https://myproject.supabase.co"
        assert project_ref == "myproject"

    def test_postgres_to_supabase_com_domain(self, converter):
        """Test extraction with .com domain."""
        postgres_url = "postgresql://postgres:key@test-123.db.supabase.com:5432/postgres"

        supabase_url, project_ref = converter.postgres_to_supabase(postgres_url, domain="supabase.com")

        assert supabase_url == "https://test-123.supabase.com"
        assert project_ref == "test-123"

    def test_postgres_to_supabase_non_supabase(self, converter):
        """Test extraction with non-Supabase PostgreSQL URL."""
        postgres_url = "postgresql://user:pass@localhost:5432/mydb"

        with pytest.raises(DatabaseURLParsingError):
            converter.postgres_to_supabase(postgres_url)

    def test_validate_conversion_supabase_to_postgres(self, converter):
        """Test validation of Supabase to PostgreSQL conversion."""
        original = "https://myproject.supabase.co"
        converted = "postgresql://postgres:key@myproject.db.supabase.co:5432/postgres"

        assert converter.validate_conversion(original, converted) is True

    def test_validate_conversion_postgres_to_supabase(self, converter):
        """Test validation of PostgreSQL to Supabase conversion."""
        original = "postgresql://postgres:key@myproject.db.supabase.co:5432/postgres"
        converted = "https://myproject.supabase.co"

        assert converter.validate_conversion(original, converted) is True

    def test_validate_conversion_invalid(self, converter):
        """Test validation with invalid conversions."""
        # Wrong conversion direction
        assert converter.validate_conversion("https://myproject.supabase.co", "https://different.supabase.co") is False

        # Non-Supabase PostgreSQL URL
        assert (
            converter.validate_conversion(
                "https://myproject.supabase.co",
                "postgresql://user:pass@localhost:5432/db",
            )
            is False
        )


class TestDatabaseURLDetector:
    """Test database URL detector functionality."""

    @pytest.fixture
    def detector(self):
        """Create detector instance."""
        return DatabaseURLDetector()

    def test_detect_supabase_url(self, detector):
        """Test detection of Supabase URLs."""
        result = detector.detect_url_type("https://myproject.supabase.co")

        assert result["type"] == "supabase"
        assert result["valid"] is True
        assert result["metadata"]["project_ref"] == "myproject"
        assert result["metadata"]["domain"] == "supabase.co"

    def test_detect_postgres_url(self, detector):
        """Test detection of PostgreSQL URLs."""
        result = detector.detect_url_type("postgresql://user:pass@host.example.com:5432/mydb?sslmode=require")

        assert result["type"] == "postgresql"
        assert result["valid"] is True
        assert result["metadata"]["hostname"] == "host.example.com"
        assert result["metadata"]["port"] == 5432
        assert result["metadata"]["database"] == "mydb"
        assert result["metadata"]["has_ssl"] is True
        assert result["metadata"]["is_supabase_postgres"] is False

    def test_detect_supabase_postgres_url(self, detector):
        """Test detection of Supabase PostgreSQL URLs."""
        result = detector.detect_url_type("postgresql://postgres:key@myproject.db.supabase.co:5432/postgres")

        assert result["type"] == "postgresql"
        assert result["valid"] is True
        assert result["metadata"]["is_supabase_postgres"] is True

    def test_detect_invalid_url(self, detector):
        """Test detection of invalid URLs."""
        result = detector.detect_url_type("not-a-url")

        assert result["type"] == "unknown"
        assert result["valid"] is False

    def test_suggest_handler_supabase(self, detector):
        """Test handler suggestions for Supabase URLs."""
        suggestion = detector.suggest_handler("https://myproject.supabase.co")

        assert "Supabase client" in suggestion
        assert "convert to PostgreSQL" in suggestion

    def test_suggest_handler_postgres(self, detector):
        """Test handler suggestions for PostgreSQL URLs."""
        suggestion = detector.suggest_handler("postgresql://user:pass@localhost:5432/db")

        assert "PostgreSQL client" in suggestion
        assert "Supabase" not in suggestion

    def test_suggest_handler_supabase_postgres(self, detector):
        """Test handler suggestions for Supabase PostgreSQL URLs."""
        suggestion = detector.suggest_handler("postgresql://postgres:key@myproject.db.supabase.co:5432/postgres")

        assert "PostgreSQL client" in suggestion
        assert "extract Supabase project" in suggestion


class TestConvenienceFunctions:
    """Test module-level convenience functions."""

    def test_convert_supabase_to_postgres(self):
        """Test convenience function for conversion."""
        result = convert_supabase_to_postgres("https://myproject.supabase.co", "test-key", use_pooler=True)

        assert "myproject.db.supabase.co:6543" in result
        assert "postgresql://" in result

    def test_detect_database_url_type(self):
        """Test convenience function for detection."""
        result = detect_database_url_type("https://myproject.supabase.co")

        assert result["type"] == "supabase"
        assert result["valid"] is True


class TestEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.fixture
    def converter(self):
        """Create converter instance."""
        return DatabaseURLConverter()

    def test_empty_url_handling(self, converter):
        """Test handling of empty URLs."""
        with pytest.raises(DatabaseURLParsingError):
            converter.supabase_to_postgres("", "password")

    def test_none_url_handling(self, converter):
        """Test handling of None URLs."""
        with pytest.raises(DatabaseURLParsingError):
            converter.supabase_to_postgres(None, "password")

    def test_malformed_url_handling(self, converter):
        """Test handling of malformed URLs."""
        malformed_urls = [
            "https://",
            "://project.supabase.co",
            "https:project.supabase.co",
            "https://project..supabase.co",
        ]

        for url in malformed_urls:
            with pytest.raises(DatabaseURLParsingError):
                converter.supabase_to_postgres(url, "password")

    def test_special_project_names(self, converter):
        """Test conversion with special characters in project names."""
        # Hyphens are allowed in project names
        result = converter.supabase_to_postgres("https://my-test-project-123.supabase.co", "password")
        assert "my-test-project-123.db.supabase.co" in result

    def test_url_with_path_ignored(self, converter):
        """Test that paths in Supabase URLs are ignored."""
        result = converter.supabase_to_postgres("https://myproject.supabase.co/some/path", "password")
        # Path should not affect the conversion
        assert "myproject.db.supabase.co:5432/postgres" in result
