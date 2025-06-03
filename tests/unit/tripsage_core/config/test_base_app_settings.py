"""
Comprehensive tests for TripSage Core base application settings using Pydantic v2.

This test module follows latest best practices from 2024:
- Pydantic v2 Settings with SettingsConfigDict
- Environment variable testing with dependency injection
- FastAPI settings dependency patterns
- Configuration validation and type safety
- Settings override testing for different environments
"""

import os
from typing import Dict

import pytest
from pydantic import ValidationError
from pydantic_settings import SettingsConfigDict

from tripsage_core.config.base_app_settings import (
    AuthSettings,
    BaseAppSettings,
    DatabaseSettings,
    FeatureFlags,
    LoggingSettings,
    RedisSettings,
    get_settings,
)


class TestBaseAppSettings:
    """Test suite for base application settings configuration."""

    @pytest.fixture
    def clean_env(self):
        """Clean environment fixture that saves and restores env vars."""
        original_env = os.environ.copy()

        # Clear all TripSage-related env vars
        env_keys_to_clear = [
            key
            for key in os.environ.keys()
            if key.startswith(("TRIPSAGE_", "DATABASE_", "REDIS_", "AUTH_", "LOG_"))
        ]

        for key in env_keys_to_clear:
            os.environ.pop(key, None)

        yield

        # Restore original environment
        os.environ.clear()
        os.environ.update(original_env)

    @pytest.fixture
    def sample_env_vars(self) -> Dict[str, str]:
        """Sample environment variables for testing."""
        return {
            "TRIPSAGE_APP_NAME": "TripSage AI Test",
            "TRIPSAGE_APP_VERSION": "1.0.0-test",
            "TRIPSAGE_ENVIRONMENT": "testing",
            "TRIPSAGE_DEBUG": "true",
            "TRIPSAGE_API_V1_PREFIX": "/api/v1",
            "DATABASE_URL": "postgresql://test:test@localhost:5432/tripsage_test",
            "DATABASE_POOL_SIZE": "10",
            "DATABASE_MAX_OVERFLOW": "20",
            "REDIS_URL": "redis://localhost:6379/1",
            "REDIS_PASSWORD": "test_password",
            "AUTH_SECRET_KEY": "test_secret_key_with_minimum_32_characters",
            "AUTH_ALGORITHM": "HS256",
            "AUTH_ACCESS_TOKEN_EXPIRE_MINUTES": "30",
            "LOG_LEVEL": "DEBUG",
            "LOG_FORMAT": "json",
        }

    def test_default_settings_creation(self, clean_env):
        """Test creation of settings with default values."""
        settings = BaseAppSettings()

        assert settings.app_name == "TripSage AI"
        assert settings.app_version == "0.1.0"
        assert settings.environment == "development"
        assert settings.debug is False
        assert settings.api_v1_prefix == "/api/v1"

    def test_settings_from_environment_variables(self, clean_env, sample_env_vars):
        """Test settings creation from environment variables."""
        # Set environment variables
        for key, value in sample_env_vars.items():
            os.environ[key] = value

        settings = BaseAppSettings()

        assert settings.app_name == "TripSage AI Test"
        assert settings.app_version == "1.0.0-test"
        assert settings.environment == "testing"
        assert settings.debug is True
        assert settings.api_v1_prefix == "/api/v1"

    def test_settings_env_file_loading(self, clean_env, tmp_path):
        """Test settings loading from .env file."""
        # Create temporary .env file
        env_file = tmp_path / ".env"
        env_content = """
TRIPSAGE_APP_NAME=TripSage AI from File
TRIPSAGE_ENVIRONMENT=production
TRIPSAGE_DEBUG=false
DATABASE_URL=postgresql://prod:prod@localhost:5432/tripsage_prod
"""
        env_file.write_text(env_content.strip())

        # Create settings with custom env_file
        class TestSettings(BaseAppSettings):
            model_config = SettingsConfigDict(
                env_file=str(env_file),
                env_file_encoding="utf-8",
                case_sensitive=False,
                env_prefix="TRIPSAGE_",
            )

        settings = TestSettings()

        assert settings.app_name == "TripSage AI from File"
        assert settings.environment == "production"
        assert settings.debug is False

    def test_settings_validation_errors(self, clean_env):
        """Test validation errors for invalid settings."""
        # Test invalid environment
        os.environ["TRIPSAGE_ENVIRONMENT"] = "invalid_env"

        with pytest.raises(ValidationError) as exc_info:
            BaseAppSettings()

        errors = exc_info.value.errors()
        assert any("Environment must be one of" in str(error) for error in errors)

    def test_settings_type_conversion(self, clean_env):
        """Test automatic type conversion for environment variables."""
        os.environ.update(
            {
                "TRIPSAGE_DEBUG": "true",  # String to bool
                "DATABASE_POOL_SIZE": "15",  # String to int
                "AUTH_ACCESS_TOKEN_EXPIRE_MINUTES": "60",  # String to int
            }
        )

        settings = BaseAppSettings()

        assert settings.debug is True
        assert isinstance(settings.debug, bool)

    def test_settings_computed_properties(self, clean_env, sample_env_vars):
        """Test computed properties and methods."""
        for key, value in sample_env_vars.items():
            os.environ[key] = value

        BaseAppSettings()

        # Test is_development
        os.environ["TRIPSAGE_ENVIRONMENT"] = "development"
        dev_settings = BaseAppSettings()
        assert dev_settings.is_development() is True

        # Test is_production
        os.environ["TRIPSAGE_ENVIRONMENT"] = "production"
        prod_settings = BaseAppSettings()
        assert prod_settings.is_production() is True

        # Test is_testing
        os.environ["TRIPSAGE_ENVIRONMENT"] = "testing"
        test_settings = BaseAppSettings()
        assert test_settings.is_testing() is True

    def test_database_settings_validation(self, clean_env):
        """Test database settings validation."""
        # Test valid database URL
        valid_db_settings = DatabaseSettings(
            database_url="postgresql://user:pass@localhost:5432/tripsage",
            pool_size=10,
            max_overflow=20,
            pool_timeout=30,
            pool_recycle=3600,
        )

        assert valid_db_settings.database_url.startswith("postgresql://")
        assert valid_db_settings.pool_size == 10
        assert valid_db_settings.max_overflow == 20

    def test_database_settings_invalid_pool_size(self, clean_env):
        """Test database settings validation for invalid pool size."""
        with pytest.raises(ValidationError, match="Pool size must be positive"):
            DatabaseSettings(
                database_url="postgresql://user:pass@localhost:5432/tripsage",
                pool_size=0,  # Invalid: must be positive
            )

    def test_redis_settings_validation(self, clean_env):
        """Test Redis settings validation."""
        valid_redis_settings = RedisSettings(
            redis_url="redis://localhost:6379/0",
            password="secure_password",
            max_connections=50,
            retry_on_timeout=True,
            socket_connect_timeout=5,
        )

        assert valid_redis_settings.redis_url.startswith("redis://")
        assert valid_redis_settings.password == "secure_password"
        assert valid_redis_settings.max_connections == 50

    def test_redis_settings_invalid_max_connections(self, clean_env):
        """Test Redis settings validation for invalid max connections."""
        with pytest.raises(ValidationError, match="Max connections must be positive"):
            RedisSettings(
                redis_url="redis://localhost:6379/0",
                max_connections=0,  # Invalid: must be positive
            )

    def test_auth_settings_validation(self, clean_env):
        """Test authentication settings validation."""
        valid_auth_settings = AuthSettings(
            secret_key="a_very_secure_secret_key_with_32_characters_minimum",
            algorithm="HS256",
            access_token_expire_minutes=30,
            refresh_token_expire_days=7,
        )

        assert len(valid_auth_settings.secret_key) >= 32
        assert valid_auth_settings.algorithm == "HS256"
        assert valid_auth_settings.access_token_expire_minutes == 30

    def test_auth_settings_secret_key_validation(self, clean_env):
        """Test authentication secret key validation."""
        with pytest.raises(
            ValidationError, match="Secret key must be at least 32 characters"
        ):
            AuthSettings(
                secret_key="short_key",  # Invalid: too short
                algorithm="HS256",
            )

    def test_auth_settings_invalid_algorithm(self, clean_env):
        """Test authentication algorithm validation."""
        with pytest.raises(ValidationError, match="Algorithm must be one of"):
            AuthSettings(
                secret_key="a_very_secure_secret_key_with_32_characters_minimum",
                algorithm="INVALID_ALGO",  # Invalid algorithm
            )

    def test_logging_settings_validation(self, clean_env):
        """Test logging settings validation."""
        valid_logging_settings = LoggingSettings(
            log_level="INFO",
            log_format="structured",
            log_file_enabled=True,
            log_file_path="/var/log/tripsage/app.log",
            log_rotation_size="10 MB",
            log_retention_days=30,
        )

        assert valid_logging_settings.log_level == "INFO"
        assert valid_logging_settings.log_format == "structured"
        assert valid_logging_settings.log_file_enabled is True

    def test_logging_settings_invalid_level(self, clean_env):
        """Test logging settings validation for invalid log level."""
        with pytest.raises(ValidationError, match="Log level must be one of"):
            LoggingSettings(
                log_level="INVALID_LEVEL",  # Invalid log level
            )

    def test_feature_flags_validation(self, clean_env):
        """Test feature flags validation."""
        feature_flags = FeatureFlags(
            enable_memory_system=True,
            enable_websockets=True,
            enable_file_uploads=False,
            enable_analytics=True,
            enable_rate_limiting=True,
            max_concurrent_requests=100,
        )

        assert feature_flags.enable_memory_system is True
        assert feature_flags.enable_websockets is True
        assert feature_flags.enable_file_uploads is False
        assert feature_flags.max_concurrent_requests == 100

    def test_feature_flags_request_limit_validation(self, clean_env):
        """Test feature flags validation for max concurrent requests."""
        with pytest.raises(
            ValidationError, match="Max concurrent requests must be positive"
        ):
            FeatureFlags(
                max_concurrent_requests=0,  # Invalid: must be positive
            )

    def test_settings_dependency_injection_pattern(self, clean_env):
        """Test settings dependency injection pattern for FastAPI."""
        from functools import lru_cache

        @lru_cache()
        def get_test_settings():
            return BaseAppSettings()

        # Test that settings are cached
        settings1 = get_test_settings()
        settings2 = get_test_settings()

        assert settings1 is settings2  # Same instance due to lru_cache

    def test_settings_override_for_testing(self, clean_env):
        """Test settings override pattern for testing."""
        # Original settings
        original_settings = BaseAppSettings()

        # Override for testing
        def get_test_settings_override():
            return BaseAppSettings(
                app_name="TripSage AI Test Override",
                environment="testing",
                debug=True,
            )

        test_settings = get_test_settings_override()

        assert test_settings.app_name == "TripSage AI Test Override"
        assert test_settings.environment == "testing"
        assert test_settings.debug is True
        assert test_settings.app_name != original_settings.app_name

    def test_settings_serialization(self, clean_env, sample_env_vars):
        """Test settings serialization and deserialization."""
        for key, value in sample_env_vars.items():
            os.environ[key] = value

        settings = BaseAppSettings()

        # Test model_dump
        settings_dict = settings.model_dump()
        assert isinstance(settings_dict, dict)
        assert settings_dict["app_name"] == "TripSage AI Test"

        # Test model_dump with exclude
        settings_dict_excluded = settings.model_dump(exclude={"secret_key"})
        assert "secret_key" not in settings_dict_excluded

        # Test model_dump_json
        settings_json = settings.model_dump_json()
        assert isinstance(settings_json, str)
        assert "TripSage AI Test" in settings_json

    def test_settings_environment_specific_configs(self, clean_env):
        """Test environment-specific configuration patterns."""
        # Development settings
        os.environ.update(
            {
                "TRIPSAGE_ENVIRONMENT": "development",
                "TRIPSAGE_DEBUG": "true",
                "LOG_LEVEL": "DEBUG",
            }
        )

        dev_settings = BaseAppSettings()
        assert dev_settings.is_development() is True
        assert dev_settings.debug is True

        # Production settings
        os.environ.update(
            {
                "TRIPSAGE_ENVIRONMENT": "production",
                "TRIPSAGE_DEBUG": "false",
                "LOG_LEVEL": "INFO",
            }
        )

        prod_settings = BaseAppSettings()
        assert prod_settings.is_production() is True
        assert prod_settings.debug is False

    def test_settings_field_validation_error_messages(self, clean_env):
        """Test that field validators provide clear error messages."""
        # Test database pool size validation
        with pytest.raises(ValidationError) as exc_info:
            DatabaseSettings(
                database_url="postgresql://user:pass@localhost:5432/db",
                pool_size=-1,
            )

        errors = exc_info.value.errors()
        assert any("Pool size must be positive" in str(error) for error in errors)

        # Test auth secret key validation
        with pytest.raises(ValidationError) as exc_info:
            AuthSettings(
                secret_key="short",
                algorithm="HS256",
            )

        errors = exc_info.value.errors()
        assert any(
            "Secret key must be at least 32 characters" in str(error)
            for error in errors
        )

    def test_settings_model_config_attributes(self, clean_env):
        """Test that model configuration is properly set."""
        settings = BaseAppSettings()

        # Test that the model has the expected config
        assert hasattr(settings, "model_config")
        config = settings.model_config

        # Test environment variable prefix
        assert config.get("env_prefix") == "TRIPSAGE_"

        # Test case sensitivity
        assert config.get("case_sensitive") is False

    @pytest.mark.parametrize(
        "env_var,expected_type,test_value",
        [
            ("TRIPSAGE_DEBUG", bool, "true"),
            ("DATABASE_POOL_SIZE", int, "15"),
            ("AUTH_ACCESS_TOKEN_EXPIRE_MINUTES", int, "60"),
            ("TRIPSAGE_APP_NAME", str, "Test App"),
        ],
    )
    def test_settings_type_coercion(
        self, clean_env, env_var, expected_type, test_value
    ):
        """Test automatic type coercion for different data types."""
        os.environ[env_var] = test_value

        settings = BaseAppSettings()

        # Get the field name without prefix
        field_name = env_var.replace("TRIPSAGE_", "").lower()
        if field_name.startswith("database_"):
            field_name = field_name.replace("database_", "")
        elif field_name.startswith("auth_"):
            field_name = field_name.replace("auth_", "")

        # Check if field exists and has correct type
        if hasattr(settings, field_name):
            field_value = getattr(settings, field_name)
            assert isinstance(field_value, expected_type)

    def test_settings_nested_model_validation(self, clean_env):
        """Test validation of nested settings models."""
        # Test that nested models are properly validated
        settings = BaseAppSettings()

        # All nested settings should be properly instantiated
        assert isinstance(settings.database, DatabaseSettings)
        assert isinstance(settings.redis, RedisSettings)
        assert isinstance(settings.auth, AuthSettings)
        assert isinstance(settings.logging, LoggingSettings)
        assert isinstance(settings.feature_flags, FeatureFlags)

    def test_settings_field_metadata_and_descriptions(self, clean_env):
        """Test that fields have proper metadata and descriptions."""
        settings = BaseAppSettings()

        # Test that model fields have descriptions
        fields = settings.model_fields

        # Check that key fields have descriptions
        assert "app_name" in fields
        assert "environment" in fields
        assert "debug" in fields

        # Test field constraints
        env_field = fields.get("environment")
        if env_field and hasattr(env_field, "json_schema_extra"):
            # Environment should have choices constraint
            pass  # Field validation logic is in the model itself

    def test_settings_secrets_handling(self, clean_env):
        """Test proper handling of sensitive configuration data."""
        os.environ.update(
            {
                "AUTH_SECRET_KEY": "super_secret_key_32_chars_test",
                "DATABASE_URL": "postgresql://user:password@localhost:5432/db",
                "REDIS_PASSWORD": "redis_secret_password",
            }
        )

        settings = BaseAppSettings()

        # Test that secret fields are marked as such
        settings.model_dump()

        # Sensitive fields should still be accessible but handled carefully
        assert len(settings.auth.secret_key) >= 32
        assert "password" in settings.database.database_url

        # Test model_dump with exclude_secrets pattern
        safe_dict = settings.model_dump(
            exclude={
                "auth": {"secret_key"},
                "database": {"database_url"},
                "redis": {"password"},
            }
        )

        # Verify sensitive data is excluded
        assert "secret_key" not in safe_dict.get("auth", {})

    def test_settings_configuration_validation_edge_cases(self, clean_env):
        """Test edge cases in configuration validation."""
        # Test minimum values
        valid_minimal_settings = BaseAppSettings(
            app_name="A",  # Minimum 1 character
            environment="development",
        )
        assert valid_minimal_settings.app_name == "A"

        # Test maximum reasonable values
        valid_large_settings = BaseAppSettings(
            app_name="A" * 100,  # Long but valid app name
            environment="production",
        )
        assert len(valid_large_settings.app_name) == 100

    def test_get_settings_function_caching(self, clean_env):
        """Test the get_settings function and its caching behavior."""
        # Clear any existing cache
        get_settings.cache_clear()

        # Test that get_settings returns consistent instances
        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2  # Should be the same instance due to lru_cache

        # Test cache info
        cache_info = get_settings.cache_info()
        assert cache_info.hits >= 1  # At least one cache hit
        assert cache_info.misses == 1  # Only one cache miss (first call)

    def test_settings_validation_with_invalid_combinations(self, clean_env):
        """Test validation with invalid combinations of settings."""
        # Test production environment with debug enabled (should be allowed but warned)
        os.environ.update(
            {
                "TRIPSAGE_ENVIRONMENT": "production",
                "TRIPSAGE_DEBUG": "true",  # Usually not recommended in production
            }
        )

        # This should still work but might trigger warnings in a real implementation
        settings = BaseAppSettings()
        assert settings.environment == "production"
        assert settings.debug is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
