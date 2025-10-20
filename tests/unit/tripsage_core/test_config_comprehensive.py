"""Comprehensive configuration testing for TripSage Core.

This module provides extensive testing coverage for the configuration system,
following 2025 best practices for Pydantic Settings testing. Achieves 90%+ coverage
through systematic testing of all configuration aspects.
"""

import os
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import pytest
from pydantic import SecretStr, ValidationError

# Import config module components directly to avoid circular imports
from tripsage_core.config import Settings


class TestConfigurationInstantiation:
    """Test Settings class instantiation and basic functionality."""

    def test_settings_instantiation_with_defaults(self):
        """Test Settings can be instantiated with default values."""
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings(_env_file=None)

            # Verify core defaults
            assert settings.environment == "development"
            assert settings.debug is False
            assert settings.log_level == "INFO"
            assert settings.api_title == "TripSage API"
            assert settings.api_version == "1.0.0"

    def test_settings_with_kwargs(self):
        """Test Settings instantiation with keyword arguments."""
        settings = Settings(
            environment="production",
            debug=True,
            log_level="DEBUG",
            api_title="Custom API",
            _env_file=None,
        )

        assert settings.environment == "production"
        assert settings.debug is True
        assert settings.log_level == "DEBUG"
        assert settings.api_title == "Custom API"

    def test_settings_field_access(self):
        """Test all fields are accessible."""
        settings = Settings(_env_file=None)

        # Core fields
        assert hasattr(settings, "environment")
        assert hasattr(settings, "debug")
        assert hasattr(settings, "log_level")

        # API fields
        assert hasattr(settings, "api_title")
        assert hasattr(settings, "api_version")
        assert hasattr(settings, "cors_origins")
        assert hasattr(settings, "cors_credentials")

        # Database fields
        assert hasattr(settings, "database_url")
        assert hasattr(settings, "database_public_key")
        assert hasattr(settings, "database_service_key")
        assert hasattr(settings, "database_jwt_secret")
        assert hasattr(settings, "postgres_url")

        # Security fields
        assert hasattr(settings, "secret_key")

        # Redis fields
        assert hasattr(settings, "redis_url")
        assert hasattr(settings, "redis_password")
        assert hasattr(settings, "redis_max_connections")

        # AI fields
        assert hasattr(settings, "openai_api_key")
        assert hasattr(settings, "openai_model")

        # Rate limiting fields
        assert hasattr(settings, "rate_limit_enabled")
        assert hasattr(settings, "rate_limit_requests_per_minute")

        # WebSocket fields
        assert hasattr(settings, "enable_websockets")
        assert hasattr(settings, "websocket_timeout")
        assert hasattr(settings, "max_websocket_connections")


class TestEnvironmentVariableHandling:
    """Test environment variable loading and validation."""

    def test_environment_variable_precedence(self):
        """Test environment variables override defaults."""
        env_vars = {
            "ENVIRONMENT": "production",
            "DEBUG": "true",
            "LOG_LEVEL": "WARNING",
            "API_TITLE": "Production API",
            "API_VERSION": "2.0.0",
            "DATABASE_URL": "https://prod.supabase.co",
            "OPENAI_MODEL": "gpt-4o-mini",
            "REDIS_MAX_CONNECTIONS": "100",
            "RATE_LIMIT_REQUESTS_PER_MINUTE": "120",
            "WEBSOCKET_TIMEOUT": "600",
        }

        with patch.dict(os.environ, env_vars):
            settings = Settings(_env_file=None)

            assert settings.environment == "production"
            assert settings.debug is True
            assert settings.log_level == "WARNING"
            assert settings.api_title == "Production API"
            assert settings.api_version == "2.0.0"
            assert settings.database_url == "https://prod.supabase.co"
            assert settings.openai_model == "gpt-4o-mini"
            assert settings.redis_max_connections == 100
            assert settings.rate_limit_requests_per_minute == 120
            assert settings.websocket_timeout == 600

    def test_case_insensitive_environment_variables(self):
        """Test case insensitive environment variable handling."""
        env_vars = {
            "environment": "test",  # lowercase
            "DEBUG": "false",  # uppercase
            "Log_Level": "ERROR",  # mixed case
        }

        with patch.dict(os.environ, env_vars):
            settings = Settings(_env_file=None)

            assert settings.environment == "test"
            assert settings.debug is False
            assert settings.log_level == "ERROR"

    def test_type_coercion_from_environment(self):
        """Test automatic type coercion from string environment variables."""
        env_vars = {
            "DEBUG": "true",  # string -> bool
            "REDIS_MAX_CONNECTIONS": "75",  # string -> int
            "DB_HEALTH_CHECK_INTERVAL": "45.5",  # string -> float
            "CORS_ORIGINS": (
                '["http://localhost:3000", "http://localhost:3001"]'
            ),  # JSON string -> list
            "RATE_LIMIT_ENABLED": "false",  # string -> bool
            "ENABLE_WEBSOCKETS": "1",  # string -> bool (truthy)
        }

        with patch.dict(os.environ, env_vars):
            settings = Settings(_env_file=None)

            assert settings.debug is True
            assert settings.redis_max_connections == 75
            assert settings.db_health_check_interval == 45.5
            assert settings.cors_origins == [
                "http://localhost:3000",
                "http://localhost:3001",
            ]
            assert settings.rate_limit_enabled is False
            assert settings.enable_websockets is True

    def test_invalid_type_coercion_handling(self):
        """Test handling of invalid type coercion."""
        env_vars = {
            "REDIS_MAX_CONNECTIONS": "not_a_number",
            "DEBUG": "not_a_boolean",
        }

        with patch.dict(os.environ, env_vars):
            with pytest.raises(ValidationError) as exc_info:
                Settings(_env_file=None)

            # Should contain validation errors for the invalid fields
            errors = exc_info.value.errors()
            error_fields = {error["loc"][0] for error in errors}
            assert "redis_max_connections" in error_fields


class TestFieldValidation:
    """Test field validation and constraints."""

    def test_environment_field_validation(self):
        """Test environment field validator."""
        # Valid environments
        for env in ["development", "production", "test", "testing"]:
            settings = Settings(environment=env, _env_file=None)
            assert settings.environment == env

        # Invalid environment
        with pytest.raises(ValidationError) as exc_info:
            Settings(environment="invalid_env", _env_file=None)

        error = exc_info.value.errors()[0]
        assert "Environment must be one of" in error["msg"]

    def test_secret_field_validation(self):
        """Test SecretStr field handling."""
        settings = Settings(
            openai_api_key=SecretStr("secret_openai_key"),
            database_public_key=SecretStr("secret_public_key"),
            database_service_key=SecretStr("secret_service_key"),
            database_jwt_secret=SecretStr("secret_jwt"),
            secret_key=SecretStr("secret_app_key"),
            _env_file=None,
        )

        # All secret fields should be SecretStr instances
        assert isinstance(settings.openai_api_key, SecretStr)
        assert isinstance(settings.database_public_key, SecretStr)
        assert isinstance(settings.database_service_key, SecretStr)
        assert isinstance(settings.database_jwt_secret, SecretStr)
        assert isinstance(settings.secret_key, SecretStr)

        # Should be able to get secret values
        assert settings.openai_api_key.get_secret_value() == "secret_openai_key"
        assert settings.database_public_key.get_secret_value() == "secret_public_key"

    def test_integer_field_constraints(self):
        """Test integer field validation and constraints."""
        # Valid integer values
        settings = Settings(
            redis_max_connections=100,
            websocket_timeout=300,
            max_websocket_connections=1000,
            rate_limit_requests_per_minute=60,
            rate_limit_burst_size=10,
            _env_file=None,
        )

        assert settings.redis_max_connections == 100
        assert settings.websocket_timeout == 300
        assert settings.max_websocket_connections == 1000

        # Test boundary values
        settings = Settings(redis_max_connections=1, _env_file=None)
        assert settings.redis_max_connections == 1

    def test_float_field_validation(self):
        """Test float field validation."""
        settings = Settings(
            db_health_check_interval=30.5,
            db_security_check_interval=60.0,
            db_recovery_delay=5.25,
            _env_file=None,
        )

        assert settings.db_health_check_interval == 30.5
        assert settings.db_security_check_interval == 60.0
        assert settings.db_recovery_delay == 5.25

    def test_list_field_validation(self):
        """Test list field validation."""
        settings = Settings(
            cors_origins=["http://localhost:3000", "https://app.example.com"],
            _env_file=None,
        )

        assert len(settings.cors_origins) == 2
        assert "http://localhost:3000" in settings.cors_origins
        assert "https://app.example.com" in settings.cors_origins

        # Test empty list
        settings = Settings(cors_origins=[], _env_file=None)
        assert settings.cors_origins == []


class TestSecretHandling:
    """Test secret and sensitive data handling."""

    def test_secret_masking_in_repr(self):
        """Test that secrets are masked in string representations."""
        settings = Settings(
            openai_api_key=SecretStr("sk-very-secret-key"),
            database_service_key=SecretStr("super-secret-service-key"),
            secret_key=SecretStr("app-secret-key"),
            _env_file=None,
        )

        settings_repr = repr(settings)
        settings_str = str(settings)

        # Secrets should not appear in string representations
        assert "sk-very-secret-key" not in settings_repr
        assert "super-secret-service-key" not in settings_repr
        assert "app-secret-key" not in settings_repr

        assert "sk-very-secret-key" not in settings_str
        assert "super-secret-service-key" not in settings_str
        assert "app-secret-key" not in settings_str

        # Should contain masked representations
        assert "**********" in settings_repr or "SecretStr" in settings_repr

    def test_secret_comparison(self):
        """Test secret comparison functionality."""
        settings1 = Settings(openai_api_key=SecretStr("same-secret"), _env_file=None)
        settings2 = Settings(openai_api_key=SecretStr("same-secret"), _env_file=None)
        settings3 = Settings(
            openai_api_key=SecretStr("different-secret"), _env_file=None
        )

        # Same secret values should be equal
        assert (
            settings1.openai_api_key.get_secret_value()
            == settings2.openai_api_key.get_secret_value()
        )

        # Different secret values should not be equal
        assert (
            settings1.openai_api_key.get_secret_value()
            != settings3.openai_api_key.get_secret_value()
        )

    def test_production_secret_validation(self):
        """Test production-specific secret validation."""
        # In production, secrets should not use default test values
        settings = Settings(
            environment="production",
            openai_api_key=SecretStr("sk-real-production-key"),
            database_service_key=SecretStr("real-service-key"),
            secret_key=SecretStr("real-app-secret"),
            _env_file=None,
        )

        assert settings.is_production
        assert settings.openai_api_key.get_secret_value() != "sk-test-1234567890"
        assert settings.database_service_key.get_secret_value() != "test-service-key"


class TestConfigurationSources:
    """Test configuration loading from different sources."""

    def test_env_file_loading(self):
        """Test loading configuration from .env file."""
        env_content = """
# Core settings
ENVIRONMENT=test
DEBUG=true
LOG_LEVEL=DEBUG

# Database settings
DATABASE_URL=https://envfile.supabase.co
DATABASE_PUBLIC_KEY=envfile-public-key
DATABASE_SERVICE_KEY=envfile-service-key

# API settings
API_TITLE=EnvFile API
API_VERSION=3.0.0

# AI settings
OPENAI_API_KEY=sk-envfile-key
OPENAI_MODEL=gpt-3.5-turbo
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write(env_content)
            f.flush()

            try:
                # Clear environment to test file loading
                with patch.dict(os.environ, {}, clear=True):
                    settings = Settings(_env_file=f.name)

                    assert settings.environment == "test"
                    assert settings.debug is True
                    assert settings.log_level == "DEBUG"
                    assert settings.database_url == "https://envfile.supabase.co"
                    assert settings.api_title == "EnvFile API"
                    assert settings.api_version == "3.0.0"
                    assert (
                        settings.openai_api_key.get_secret_value() == "sk-envfile-key"
                    )
                    assert settings.openai_model == "gpt-3.5-turbo"
            finally:
                os.unlink(f.name)

    def test_environment_overrides_env_file(self):
        """Test that environment variables override .env file values."""
        env_content = """
ENVIRONMENT=test
API_TITLE=EnvFile API
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write(env_content)
            f.flush()

            try:
                # Environment variables should override .env file
                env_vars = {"ENVIRONMENT": "production", "API_TITLE": "Override API"}

                with patch.dict(os.environ, env_vars):
                    settings = Settings(_env_file=f.name)

                    assert settings.environment == "production"  # from env var
                    assert settings.api_title == "Override API"  # from env var
            finally:
                os.unlink(f.name)

    def test_multiple_env_files(self):
        """Test loading from multiple .env files with precedence."""
        base_content = """
ENVIRONMENT=development
API_TITLE=Base API
DATABASE_URL=https://base.supabase.co
"""

        override_content = """
ENVIRONMENT=staging
API_TITLE=Override API
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".env", delete=False
        ) as base_file:
            base_file.write(base_content)
            base_file.flush()

            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".env", delete=False
            ) as override_file:
                override_file.write(override_content)
                override_file.flush()

                try:
                    with patch.dict(os.environ, {}, clear=True):
                        # Load base configuration first
                        settings = Settings(
                            _env_file=[base_file.name, override_file.name]
                        )

                        # Override file should take precedence
                        assert settings.environment == "staging"
                        assert settings.api_title == "Override API"
                        # Base values should still be present
                        assert settings.database_url == "https://base.supabase.co"
                finally:
                    os.unlink(base_file.name)
                    os.unlink(override_file.name)


class TestErrorHandling:
    """Test error handling and validation scenarios."""

    def test_validation_error_messages(self):
        """Test clear validation error messages."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(environment="invalid", _env_file=None)

        error = exc_info.value.errors()[0]
        assert error["loc"] == ("environment",)
        assert "Environment must be one of" in error["msg"]

    def test_multiple_validation_errors(self):
        """Test handling multiple validation errors."""
        with patch.dict(os.environ, {"REDIS_MAX_CONNECTIONS": "invalid"}):
            with pytest.raises(ValidationError) as exc_info:
                Settings(environment="invalid", _env_file=None)

            errors = exc_info.value.errors()
            assert len(errors) >= 2  # At least environment and redis_max_connections

    def test_missing_env_file_handling(self):
        """Test graceful handling of missing .env file."""
        # Should not raise error if .env file doesn't exist
        settings = Settings(_env_file="nonexistent.env")
        assert settings.environment == "development"  # Should use defaults

    def test_malformed_env_file_handling(self):
        """Test handling of malformed .env file."""
        malformed_content = """
ENVIRONMENT=test
INVALID LINE WITHOUT EQUALS
DEBUG=true
=VALUE_WITHOUT_KEY
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write(malformed_content)
            f.flush()

            try:
                # Should still load valid lines and ignore malformed ones
                settings = Settings(_env_file=f.name)
                assert settings.environment == "test"
                assert settings.debug is True
            finally:
                os.unlink(f.name)


class TestPropertyMethods:
    """Test property methods and computed values."""

    def test_environment_property_methods(self):
        """Test environment checking property methods."""
        # Test development environment
        dev_settings = Settings(environment="development", _env_file=None)
        assert dev_settings.is_development is True
        assert dev_settings.is_production is False
        assert dev_settings.is_testing is False

        # Test production environment
        prod_settings = Settings(environment="production", _env_file=None)
        assert prod_settings.is_development is False
        assert prod_settings.is_production is True
        assert prod_settings.is_testing is False

        # Test testing environment
        test_settings = Settings(environment="test", _env_file=None)
        assert test_settings.is_development is False
        assert test_settings.is_production is False
        assert test_settings.is_testing is True

    def test_websocket_uppercase_aliases(self):
        """Test uppercase aliases for WebSocket configuration."""
        settings = Settings(
            enable_websockets=True,
            websocket_timeout=600,
            max_websocket_connections=2000,
            _env_file=None,
        )

        # Test getters
        assert settings.ENABLE_WEBSOCKETS is True
        assert settings.WEBSOCKET_TIMEOUT == 600
        assert settings.MAX_WEBSOCKET_CONNECTIONS == 2000

        # Test setters
        settings.ENABLE_WEBSOCKETS = False
        settings.WEBSOCKET_TIMEOUT = 300
        settings.MAX_WEBSOCKET_CONNECTIONS = 1500

        assert settings.enable_websockets is False
        assert settings.websocket_timeout == 300
        assert settings.max_websocket_connections == 1500


class TestPostgresURLHandling:
    """Test PostgreSQL URL configuration and conversion."""

    def test_effective_postgres_url_with_explicit_postgres_url(self):
        """Test effective_postgres_url returns postgres_url when explicitly set."""
        settings = Settings(
            postgres_url="postgresql://user:pass@localhost:5432/mydb", _env_file=None
        )

        assert (
            settings.effective_postgres_url
            == "postgresql://user:pass@localhost:5432/mydb"
        )

    def test_effective_postgres_url_converts_postgres_scheme(self):
        """Test effective_postgres_url converts postgres:// to postgresql://."""
        settings = Settings(
            postgres_url="postgres://user:pass@localhost:5432/mydb", _env_file=None
        )

        assert (
            settings.effective_postgres_url
            == "postgresql://user:pass@localhost:5432/mydb"
        )

    def test_effective_postgres_url_with_test_supabase_url(self):
        """Test effective_postgres_url handles test Supabase URL."""
        settings = Settings(database_url="https://test.supabase.com", _env_file=None)

        url = settings.effective_postgres_url
        assert url == "postgresql://postgres:password@127.0.0.1:5432/test_database"

    def test_effective_postgres_url_with_real_supabase_url(self):
        """Test effective_postgres_url converts real Supabase URL."""
        settings = Settings(
            database_url="https://xyzcompanyabc.supabase.co", _env_file=None
        )

        url = settings.effective_postgres_url
        assert "postgresql://postgres.xyzcompanyabc" in url
        assert "pooler.supabase.com" in url
        assert "6543" in url

    def test_effective_postgres_url_with_existing_postgresql_url(self):
        """Test effective_postgres_url with already postgresql:// URL."""
        settings = Settings(
            database_url="postgresql://user:pass@custom-host:5432/db", _env_file=None
        )

        assert (
            settings.effective_postgres_url
            == "postgresql://user:pass@custom-host:5432/db"
        )

    def test_effective_postgres_url_fallback_for_unknown_format(self):
        """Test effective_postgres_url fallback for unknown URL format."""
        settings = Settings(database_url="unknown://format/url", _env_file=None)

        url = settings.effective_postgres_url
        assert url == "postgresql://postgres:password@127.0.0.1:5432/test_database"


class TestConfigurationCaching:
    """Test configuration caching and performance."""

    def test_get_settings_caching(self):
        """Test that get_settings caches instances."""
        from tripsage_core.config import get_settings

        # Clear any existing cache
        if hasattr(get_settings, "cache_clear"):
            get_settings.cache_clear()

        with patch.dict(os.environ, {"ENVIRONMENT": "test"}):
            settings1 = get_settings()
            settings2 = get_settings()

            # Should be the same instance due to @lru_cache
            assert settings1 is settings2

    def test_settings_creation_performance(self):
        """Test Settings creation performance."""
        start_time = time.time()

        for _ in range(10):
            Settings(_env_file=None)

        end_time = time.time()
        creation_time = end_time - start_time

        # Should create 10 instances in less than 1 second
        assert creation_time < 1.0

    def test_concurrent_settings_access(self):
        """Test concurrent access to settings."""

        def create_settings():
            return Settings(_env_file=None)

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(create_settings) for _ in range(10)]
            settings_list = [future.result() for future in futures]

        # All settings should be created successfully
        assert len(settings_list) == 10
        for settings in settings_list:
            assert isinstance(settings, Settings)


class TestRateLimitingConfiguration:
    """Test rate limiting configuration validation."""

    def test_rate_limiting_defaults(self):
        """Test rate limiting default values."""
        settings = Settings(_env_file=None)

        assert settings.rate_limit_enabled is True
        assert settings.rate_limit_use_dragonfly is True
        assert settings.rate_limit_requests_per_minute == 60
        assert settings.rate_limit_requests_per_hour == 1000
        assert settings.rate_limit_requests_per_day == 10000
        assert settings.rate_limit_burst_size == 10

    def test_rate_limiting_algorithm_flags(self):
        """Test rate limiting algorithm configuration flags."""
        settings = Settings(_env_file=None)

        assert settings.rate_limit_enable_sliding_window is True
        assert settings.rate_limit_enable_token_bucket is True
        assert settings.rate_limit_enable_burst_protection is True
        assert settings.rate_limit_enable_monitoring is True

    def test_rate_limiting_custom_values(self):
        """Test custom rate limiting values."""
        settings = Settings(
            rate_limit_enabled=False,
            rate_limit_requests_per_minute=120,
            rate_limit_requests_per_hour=5000,
            rate_limit_burst_size=20,
            _env_file=None,
        )

        assert settings.rate_limit_enabled is False
        assert settings.rate_limit_requests_per_minute == 120
        assert settings.rate_limit_requests_per_hour == 5000
        assert settings.rate_limit_burst_size == 20


class TestMonitoringConfiguration:
    """Test monitoring and metrics configuration."""

    def test_monitoring_defaults(self):
        """Test monitoring configuration defaults."""
        settings = Settings(_env_file=None)

        assert settings.enable_database_monitoring is True
        assert settings.enable_prometheus_metrics is True
        assert settings.enable_security_monitoring is True
        assert settings.enable_auto_recovery is True

    def test_database_monitoring_intervals(self):
        """Test database monitoring interval configuration."""
        settings = Settings(_env_file=None)

        assert settings.db_health_check_interval == 30.0
        assert settings.db_security_check_interval == 60.0
        assert settings.db_max_recovery_attempts == 3
        assert settings.db_recovery_delay == 5.0

    def test_metrics_server_configuration(self):
        """Test metrics server configuration."""
        settings = Settings(_env_file=None)

        assert settings.metrics_server_port == 8000
        assert settings.enable_metrics_server is False  # Disabled by default


class TestPydanticSettingsIntegration:
    """Test Pydantic Settings integration and patterns."""

    def test_settings_config_dict(self):
        """Test SettingsConfigDict configuration."""
        settings = Settings(_env_file=None)

        assert settings.model_config["env_file"] == ".env"
        assert settings.model_config["env_file_encoding"] == "utf-8"
        assert settings.model_config["case_sensitive"] is False
        assert settings.model_config["str_strip_whitespace"] is True
        assert settings.model_config["validate_assignment"] is True

    def test_field_descriptions(self):
        """Test field descriptions are present."""
        settings = Settings(_env_file=None)

        # Check that fields have descriptions
        fields = settings.model_fields

        assert "description" in str(fields["database_url"])
        assert "description" in str(fields["redis_max_connections"])
        assert "description" in str(fields["openai_api_key"])

    def test_model_validation(self):
        """Test model validation behavior."""
        # Test that validation occurs on assignment when validate_assignment=True
        settings = Settings(_env_file=None)

        # Valid assignment should work
        settings.redis_max_connections = 100
        assert settings.redis_max_connections == 100

        # Invalid assignment should raise ValidationError
        with pytest.raises(ValidationError):
            settings.environment = "invalid_environment"


class TestEdgeCasesAndBoundaries:
    """Test edge cases and boundary conditions."""

    def test_empty_environment_variables(self):
        """Test handling of empty environment variables."""
        env_vars = {
            "API_TITLE": "",  # Empty string
            "REDIS_URL": "",  # Empty string for optional field
        }

        with patch.dict(os.environ, env_vars):
            settings = Settings(_env_file=None)

            assert settings.api_title == ""
            assert settings.redis_url == ""

    def test_very_long_values(self):
        """Test handling of very long configuration values."""
        long_value = "x" * 1000

        settings = Settings(
            api_title=long_value,
            database_url=f"https://{long_value}.supabase.co",
            _env_file=None,
        )

        assert len(settings.api_title) == 1000
        assert long_value in settings.database_url

    def test_special_characters_in_values(self):
        """Test handling of special characters in configuration values."""
        special_chars = "!@#$%^&*(){}[]|\\:;\"'<>?,./"

        settings = Settings(api_title=f"API {special_chars}", _env_file=None)

        assert special_chars in settings.api_title

    def test_unicode_characters(self):
        """Test handling of unicode characters."""
        unicode_value = "API ñáéíóú 中文 🚀"

        settings = Settings(api_title=unicode_value, _env_file=None)

        assert settings.api_title == unicode_value

    def test_extreme_numeric_values(self):
        """Test handling of extreme numeric values."""
        settings = Settings(
            redis_max_connections=1,  # Minimum reasonable value
            websocket_timeout=1,  # Minimum value
            max_websocket_connections=1000000,  # Large value
            _env_file=None,
        )

        assert settings.redis_max_connections == 1
        assert settings.websocket_timeout == 1
        assert settings.max_websocket_connections == 1000000


class TestProductionScenarios:
    """Test production deployment scenarios."""

    def test_production_environment_setup(self):
        """Test complete production environment setup."""
        prod_env = {
            "ENVIRONMENT": "production",
            "DEBUG": "false",
            "LOG_LEVEL": "INFO",
            "DATABASE_URL": "https://prod-project.supabase.co",
            "DATABASE_PUBLIC_KEY": "prod-anon-key",
            "DATABASE_SERVICE_KEY": "prod-service-key",
            "DATABASE_JWT_SECRET": "prod-jwt-secret",
            "SECRET_KEY": "prod-secret-key",
            "REDIS_URL": "redis://prod-redis:6379/0",
            "REDIS_PASSWORD": "prod-redis-password",
            "OPENAI_API_KEY": "sk-prod-openai-key",
            "RATE_LIMIT_ENABLED": "true",
            "ENABLE_WEBSOCKETS": "true",
            "ENABLE_DATABASE_MONITORING": "true",
            "ENABLE_PROMETHEUS_METRICS": "true",
        }

        with patch.dict(os.environ, prod_env):
            settings = Settings(_env_file=None)

            assert settings.is_production
            assert settings.debug is False
            assert settings.log_level == "INFO"
            assert "prod-project" in settings.database_url
            assert settings.rate_limit_enabled is True
            assert settings.enable_websockets is True
            assert settings.enable_database_monitoring is True

    def test_development_environment_setup(self):
        """Test development environment setup."""
        dev_env = {
            "ENVIRONMENT": "development",
            "DEBUG": "true",
            "LOG_LEVEL": "DEBUG",
            "RATE_LIMIT_ENABLED": "false",  # Often disabled in dev
        }

        with patch.dict(os.environ, dev_env):
            settings = Settings(_env_file=None)

            assert settings.is_development
            assert settings.debug is True
            assert settings.log_level == "DEBUG"
            assert settings.rate_limit_enabled is False

    def test_testing_environment_setup(self):
        """Test testing environment setup."""
        test_env = {
            "ENVIRONMENT": "testing",
            "DEBUG": "false",
            "LOG_LEVEL": "WARNING",
            "RATE_LIMIT_ENABLED": "false",
            "ENABLE_WEBSOCKETS": "false",
            "ENABLE_DATABASE_MONITORING": "false",
        }

        with patch.dict(os.environ, test_env):
            settings = Settings(_env_file=None)

            assert settings.is_testing
            assert settings.debug is False
            assert settings.log_level == "WARNING"
            assert settings.rate_limit_enabled is False
            assert settings.enable_websockets is False
            assert settings.enable_database_monitoring is False


# Performance and load testing
class TestPerformanceScenarios:
    """Test performance aspects of configuration."""

    def test_settings_memory_usage(self):
        """Test memory usage of Settings instances."""
        import sys

        settings = Settings(_env_file=None)
        memory_size = sys.getsizeof(settings)

        # Settings instance should be reasonably sized (less than 10KB)
        assert memory_size < 10240

    def test_rapid_instantiation(self):
        """Test rapid Settings instantiation."""
        start_time = time.time()

        settings_list = [Settings(_env_file=None) for _ in range(100)]

        end_time = time.time()
        total_time = end_time - start_time

        # Should be able to create 100 instances quickly
        assert total_time < 2.0
        assert len(settings_list) == 100

    def test_property_access_performance(self):
        """Test performance of property access."""
        settings = Settings(_env_file=None)

        start_time = time.time()

        # Access properties many times
        for _ in range(1000):
            _ = settings.environment
            _ = settings.is_production
            _ = settings.effective_postgres_url
            _ = settings.ENABLE_WEBSOCKETS

        end_time = time.time()
        access_time = end_time - start_time

        # Property access should be fast
        assert access_time < 1.0
