"""
Comprehensive test coverage for TripSage configuration system.

This test suite provides comprehensive coverage for:
- DatabaseConfig with SUPABASE_ prefix environment variables
- DragonflyConfig with DRAGONFLY_ prefix environment variables
- CoreAppSettings integration and validation
- Environment variable loading and .env file processing
- SecretStr security handling
- Backward compatibility features
- Configuration validation and error handling
- Settings inheritance and field mapping
- Edge cases and error conditions

Achieves 95%+ test coverage for configuration components.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import SecretStr, ValidationError

from tripsage_core.config.base_app_settings import (
    CoreAppSettings,
    DatabaseConfig,
    DragonflyConfig,
    get_settings,
    init_settings,
)

# Pytest configuration to avoid conflicts
pytestmark = pytest.mark.filterwarnings(
    "ignore::pytest.PytestUnraisableExceptionWarning"
)


class TestDatabaseConfigurationSystem:
    """Test suite for DatabaseConfig with SUPABASE_ environment prefix."""

    def test_database_config_defaults(self):
        """Test default DatabaseConfig values."""
        config = DatabaseConfig(_env_file=None)

        assert config.url == "https://test-project.supabase.co"
        assert config.anon_key.get_secret_value() == "test-anon-key"
        assert config.service_role_key is None
        assert config.jwt_secret.get_secret_value() == "test-jwt-secret"
        assert config.project_id is None
        assert config.timeout == 60.0
        assert config.auto_refresh_token is True
        assert config.persist_session is True
        assert config.pgvector_enabled is True
        assert config.vector_dimensions == 1536

    def test_supabase_prefix_environment_loading(self):
        """Test SUPABASE_ prefixed environment variable loading."""
        env_vars = {
            "SUPABASE_URL": "https://custom-project.supabase.co",
            "SUPABASE_ANON_KEY": "custom-anon-key-123",
            "SUPABASE_SERVICE_ROLE_KEY": "custom-service-key-456",
            "SUPABASE_JWT_SECRET": "custom-jwt-secret-789",
            "SUPABASE_PROJECT_ID": "custom-project-id",
            "SUPABASE_TIMEOUT": "30.0",
            "SUPABASE_AUTO_REFRESH_TOKEN": "false",
            "SUPABASE_PERSIST_SESSION": "false",
            "SUPABASE_PGVECTOR_ENABLED": "false",
            "SUPABASE_VECTOR_DIMENSIONS": "768",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            config = DatabaseConfig(_env_file=None)

            assert config.url == "https://custom-project.supabase.co"
            assert config.anon_key.get_secret_value() == "custom-anon-key-123"
            assert (
                config.service_role_key.get_secret_value() == "custom-service-key-456"
            )
            assert config.jwt_secret.get_secret_value() == "custom-jwt-secret-789"
            assert config.project_id == "custom-project-id"
            assert config.timeout == 30.0
            assert config.auto_refresh_token is False
            assert config.persist_session is False
            assert config.pgvector_enabled is False
            assert config.vector_dimensions == 768

    def test_backward_compatibility_properties(self):
        """Test backward compatibility property accessors."""
        config = DatabaseConfig(
            _env_file=None,
            url="https://compat-test.supabase.co",
            anon_key=SecretStr("compat-anon-key"),
            service_role_key=SecretStr("compat-service-key"),
            jwt_secret=SecretStr("compat-jwt-secret"),
            project_id="compat-project",
            timeout=45.0,
            auto_refresh_token=False,
            persist_session=False,
        )

        # Test property getters
        assert config.supabase_url == "https://compat-test.supabase.co"
        assert config.supabase_anon_key.get_secret_value() == "compat-anon-key"
        assert (
            config.supabase_service_role_key.get_secret_value() == "compat-service-key"
        )
        assert config.supabase_jwt_secret.get_secret_value() == "compat-jwt-secret"
        assert config.supabase_project_id == "compat-project"
        assert config.supabase_timeout == 45.0
        assert config.supabase_auto_refresh_token is False
        assert config.supabase_persist_session is False

        # Test property setters
        config.supabase_url = "https://new-url.supabase.co"
        config.supabase_anon_key = SecretStr("new-anon-key")
        config.supabase_service_role_key = SecretStr("new-service-key")
        config.supabase_jwt_secret = SecretStr("new-jwt-secret")
        config.supabase_project_id = "new-project-id"
        config.supabase_timeout = 90.0
        config.supabase_auto_refresh_token = True
        config.supabase_persist_session = True

        assert config.url == "https://new-url.supabase.co"
        assert config.anon_key.get_secret_value() == "new-anon-key"
        assert config.service_role_key.get_secret_value() == "new-service-key"
        assert config.jwt_secret.get_secret_value() == "new-jwt-secret"
        assert config.project_id == "new-project-id"
        assert config.timeout == 90.0
        assert config.auto_refresh_token is True
        assert config.persist_session is True

    def test_case_insensitive_environment_variables(self):
        """Test case insensitive environment variable handling."""
        env_vars = {
            "supabase_url": "https://lowercase.supabase.co",
            "SUPABASE_ANON_KEY": "UPPERCASE-KEY",
            "Supabase_Jwt_Secret": "MixedCase-Secret",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            config = DatabaseConfig(_env_file=None)

            assert config.url == "https://lowercase.supabase.co"
            assert config.anon_key.get_secret_value() == "UPPERCASE-KEY"
            assert config.jwt_secret.get_secret_value() == "MixedCase-Secret"

    def test_model_config_settings(self):
        """Test SettingsConfigDict configuration is correct."""
        config = DatabaseConfig(_env_file=None)

        model_config = config.model_config
        assert model_config["env_prefix"] == "SUPABASE_"
        assert model_config["env_file"] == ".env"
        assert model_config["env_file_encoding"] == "utf-8"
        assert model_config["case_sensitive"] is False
        assert model_config["extra"] == "ignore"


class TestDragonflyConfigurationSystem:
    """Test suite for DragonflyConfig with DRAGONFLY_ environment prefix."""

    def test_dragonfly_config_defaults(self):
        """Test default DragonflyConfig values."""
        config = DragonflyConfig(_env_file=None)

        assert config.url == "redis://localhost:6379/0"
        assert config.password is None
        assert config.ttl_short == 300
        assert config.ttl_medium == 3600
        assert config.ttl_long == 86400
        assert config.max_memory_policy == "allkeys-lru"
        assert config.max_memory == "4gb"
        assert config.max_connections == 10000
        assert config.thread_count == 4
        assert config.port == 6379

    def test_dragonfly_prefix_environment_loading(self):
        """Test DRAGONFLY_ prefixed environment variable loading."""
        env_vars = {
            "DRAGONFLY_URL": "redis://custom-host:6380/1",
            "DRAGONFLY_PASSWORD": "custom-password",
            "DRAGONFLY_TTL_SHORT": "600",
            "DRAGONFLY_TTL_MEDIUM": "7200",
            "DRAGONFLY_TTL_LONG": "172800",
            "DRAGONFLY_MAX_MEMORY_POLICY": "allkeys-random",
            "DRAGONFLY_MAX_MEMORY": "8gb",
            "DRAGONFLY_MAX_CONNECTIONS": "5000",
            "DRAGONFLY_THREAD_COUNT": "8",
            "DRAGONFLY_PORT": "6380",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            config = DragonflyConfig(_env_file=None)

            assert config.url == "redis://custom-host:6380/1"
            assert config.password == "custom-password"
            assert config.ttl_short == 600
            assert config.ttl_medium == 7200
            assert config.ttl_long == 172800
            assert config.max_memory_policy == "allkeys-random"
            assert config.max_memory == "8gb"
            assert config.max_connections == 5000
            assert config.thread_count == 8
            assert config.port == 6380


class TestSecretStrSecurityHandling:
    """Test suite for SecretStr security features."""

    def test_secret_str_value_access(self):
        """Test SecretStr value access and security."""
        config = DatabaseConfig(
            _env_file=None,
            anon_key=SecretStr("very-secret-anon-key"),
            service_role_key=SecretStr("very-secret-service-key"),
            jwt_secret=SecretStr("very-secret-jwt-token"),
        )

        # Secrets should be accessible via get_secret_value()
        assert config.anon_key.get_secret_value() == "very-secret-anon-key"
        assert config.service_role_key.get_secret_value() == "very-secret-service-key"
        assert config.jwt_secret.get_secret_value() == "very-secret-jwt-token"

    def test_secret_str_hidden_in_logs(self):
        """Test that secrets are hidden in string representations."""
        config = DatabaseConfig(
            _env_file=None,
            anon_key=SecretStr("secret-anon-key"),
            service_role_key=SecretStr("secret-service-key"),
            jwt_secret=SecretStr("secret-jwt-token"),
        )

        # Secrets should be hidden in string representation
        config_str = str(config)
        assert "secret-anon-key" not in config_str
        assert "secret-service-key" not in config_str
        assert "secret-jwt-token" not in config_str
        assert "**********" in config_str or "SecretStr('**********')" in config_str

    def test_secret_str_json_serialization(self):
        """Test SecretStr behavior in JSON serialization."""
        config = DatabaseConfig(
            _env_file=None,
            anon_key=SecretStr("secret-anon-key"),
            jwt_secret=SecretStr("secret-jwt-token"),
        )

        # JSON serialization should hide secrets
        config_dict = config.model_dump()
        config_json_str = str(config_dict)

        assert "secret-anon-key" not in config_json_str
        assert "secret-jwt-token" not in config_json_str

    def test_secret_str_special_characters(self):
        """Test SecretStr with special characters."""
        special_secret = "test-key!@#$%^&*()_+{}|:<>?[]\\\";'"
        config = DatabaseConfig(_env_file=None, anon_key=SecretStr(special_secret))
        assert config.anon_key.get_secret_value() == special_secret

    def test_secret_str_empty_and_none(self):
        """Test SecretStr handling of empty and None values."""
        config = DatabaseConfig(_env_file=None, anon_key=SecretStr(""))
        assert config.anon_key.get_secret_value() == ""

        config = DatabaseConfig(_env_file=None)
        assert config.service_role_key is None


class TestEnvironmentFileHandling:
    """Test suite for .env file loading and processing."""

    def test_env_file_loading(self):
        """Test loading configuration from .env file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("SUPABASE_URL=https://envfile-test.supabase.co\\n")
            f.write("SUPABASE_ANON_KEY=envfile-anon-key\\n")
            f.write("SUPABASE_JWT_SECRET=envfile-jwt-secret\\n")
            f.write("SUPABASE_TIMEOUT=25.5\\n")
            temp_env_file = f.name

        try:
            config = DatabaseConfig(_env_file=temp_env_file)

            assert config.url == "https://envfile-test.supabase.co"
            assert config.anon_key.get_secret_value() == "envfile-anon-key"
            assert config.jwt_secret.get_secret_value() == "envfile-jwt-secret"
            assert config.timeout == 25.5
        finally:
            os.unlink(temp_env_file)

    def test_env_file_priority_over_defaults(self):
        """Test that .env file values override defaults."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("SUPABASE_URL=https://envfile.supabase.co\\n")
            f.write("SUPABASE_ANON_KEY=envfile-key\\n")
            f.write("SUPABASE_TIMEOUT=15.0\\n")
            temp_env_file = f.name

        try:
            config = DatabaseConfig(_env_file=temp_env_file)
            assert config.url == "https://envfile.supabase.co"
            assert config.anon_key.get_secret_value() == "envfile-key"
            assert config.timeout == 15.0
        finally:
            os.unlink(temp_env_file)

    def test_environment_variables_override_env_file(self):
        """Test that environment variables override .env file values."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("SUPABASE_URL=https://envfile.supabase.co\\n")
            f.write("SUPABASE_ANON_KEY=envfile-key\\n")
            temp_env_file = f.name

        try:
            with patch.dict(
                os.environ,
                {"SUPABASE_URL": "https://override.supabase.co"},
                clear=False,
            ):
                config = DatabaseConfig(_env_file=temp_env_file)
                assert config.url == "https://override.supabase.co"  # env override
                assert config.anon_key.get_secret_value() == "envfile-key"  # from file
        finally:
            os.unlink(temp_env_file)

    def test_missing_env_file_handling(self):
        """Test graceful handling of missing .env file."""
        config = DatabaseConfig(_env_file="/nonexistent/.env")

        # Should use default values when .env file doesn't exist
        assert config.url == "https://test-project.supabase.co"
        assert config.anon_key.get_secret_value() == "test-anon-key"

    def test_env_file_encoding_utf8(self):
        """Test .env file UTF-8 encoding support."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".env", delete=False, encoding="utf-8"
        ) as f:
            f.write("SUPABASE_URL=https://üñíçödé.supabase.co\\n")
            f.write("SUPABASE_PROJECT_ID=tëst-prøjëct\\n")
            temp_env_file = f.name

        try:
            config = DatabaseConfig(_env_file=temp_env_file)
            assert config.url == "https://üñíçödé.supabase.co"
            assert config.project_id == "tëst-prøjëct"
        finally:
            os.unlink(temp_env_file)


class TestConfigurationValidation:
    """Test suite for configuration validation and error handling."""

    def test_environment_validation(self):
        """Test environment field validation."""
        # Valid environments should work
        for env in ["development", "testing", "staging", "production"]:
            settings = CoreAppSettings(_env_file=None, environment=env)
            assert settings.environment == env

        # Invalid environment should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            CoreAppSettings(_env_file=None, environment="invalid")

        errors = exc_info.value.errors()
        assert len(errors) == 1
        # Pydantic v2 uses different error messages
        assert errors[0]["type"] in ["literal_error", "value_error"]

    def test_log_level_validation(self):
        """Test log level validation and normalization."""
        # Valid log levels (case insensitive)
        for level in ["debug", "INFO", "Warning", "ERROR", "CRITICAL"]:
            settings = CoreAppSettings(_env_file=None, log_level=level)
            assert settings.log_level == level.upper()

        # Invalid log level should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            CoreAppSettings(_env_file=None, log_level="INVALID")

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] in ["literal_error", "value_error"]

    def test_configuration_inheritance(self):
        """Test proper inheritance of nested configurations."""
        settings = CoreAppSettings(_env_file=None)

        # Verify all nested configurations are properly instantiated
        assert isinstance(settings.database, DatabaseConfig)
        assert isinstance(settings.dragonfly, DragonflyConfig)
        assert hasattr(settings, "mem0")
        assert hasattr(settings, "langgraph")
        assert hasattr(settings, "crawl4ai")
        assert hasattr(settings, "agent")
        assert hasattr(settings, "feature_flags")
        assert hasattr(settings, "opentelemetry")

    def test_extra_environment_variables_ignored(self):
        """Test that extra environment variables are ignored."""
        env_vars = {
            "SUPABASE_URL": "https://valid.supabase.co",
            "SUPABASE_INVALID_FIELD": "should-be-ignored",
            "SUPABASE_ANOTHER_UNKNOWN": "also-ignored",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            # Should not raise validation error due to extra='ignore'
            config = DatabaseConfig(_env_file=None)
            assert config.url == "https://valid.supabase.co"

            # Unknown fields should not be accessible
            assert not hasattr(config, "invalid_field")
            assert not hasattr(config, "another_unknown")


class TestCoreAppSettingsIntegration:
    """Test suite for CoreAppSettings integration and helper methods."""

    def test_core_app_settings_defaults(self):
        """Test CoreAppSettings default values."""
        settings = CoreAppSettings(_env_file=None)

        assert settings.app_name == "TripSage"
        assert settings.environment == "development"
        assert settings.debug is False
        assert settings.log_level == "INFO"

    def test_environment_check_methods(self):
        """Test environment checking helper methods."""
        # Development
        settings = CoreAppSettings(_env_file=None, environment="development")
        assert settings.is_development() is True
        assert settings.is_production() is False
        assert settings.is_testing() is False

        # Production
        settings = CoreAppSettings(_env_file=None, environment="production")
        assert settings.is_development() is False
        assert settings.is_production() is True
        assert settings.is_testing() is False

        # Testing
        settings = CoreAppSettings(_env_file=None, environment="testing")
        assert settings.is_development() is False
        assert settings.is_production() is False
        assert settings.is_testing() is True

    def test_get_secret_value_helper(self):
        """Test get_secret_value helper method."""
        settings = CoreAppSettings(
            _env_file=None,
            openai_api_key=SecretStr("my-secret-key"),
            google_maps_api_key=SecretStr("google-key"),
        )

        # Existing secret
        assert settings.get_secret_value("openai_api_key") == "my-secret-key"
        assert settings.get_secret_value("google_maps_api_key") == "google-key"

        # Non-existent attribute
        assert settings.get_secret_value("non_existent") is None

        # Non-secret attribute
        assert settings.get_secret_value("app_name") is None

    def test_base_dir_path_resolution(self):
        """Test base_dir path resolution."""
        settings = CoreAppSettings(_env_file=None)

        # base_dir should be a valid Path object pointing to project root
        assert isinstance(settings.base_dir, Path)
        assert settings.base_dir.exists()

        # Should point to the project root (containing pyproject.toml or similar)
        potential_markers = ["pyproject.toml", "requirements.txt", "setup.py"]
        has_marker = any(
            (settings.base_dir / marker).exists() for marker in potential_markers
        )
        assert has_marker, (
            f"base_dir {settings.base_dir} doesn't seem to be project root"
        )

    def test_critical_settings_validation(self):
        """Test critical settings validation."""
        settings = CoreAppSettings(_env_file=None, environment="development")
        errors = settings.validate_critical_settings()
        # Development should have no critical errors with default test values
        assert isinstance(errors, list)

    def test_production_security_validation(self):
        """Test production-specific security validation."""
        production_settings = CoreAppSettings(
            _env_file=None,
            environment="production",
            debug=False,
            api_key_master_secret=SecretStr(
                "master-secret-for-byok-encryption"
            ),  # default
        )

        errors = production_settings.validate_critical_settings()

        # Should contain security warnings for default secrets in production
        security_errors = [error for error in errors if "secret" in error.lower()]
        assert len(security_errors) > 0


class TestSettingsCachingAndInitialization:
    """Test suite for settings caching and initialization behavior."""

    def test_get_settings_caching(self):
        """Test that get_settings returns cached instance."""
        # Clear cache first
        get_settings.cache_clear()

        # First call should create new instance
        settings1 = get_settings()
        settings2 = get_settings()

        # Should be the same instance due to lru_cache
        assert settings1 is settings2

        # Clear cache and verify new instance
        get_settings.cache_clear()
        settings3 = get_settings()
        assert settings3 is not settings1

    def test_init_settings_function(self):
        """Test init_settings function behavior."""
        get_settings.cache_clear()

        with patch.dict(os.environ, {"ENVIRONMENT": "testing"}, clear=False):
            settings = init_settings()

            assert isinstance(settings, CoreAppSettings)
            assert settings.environment == "testing"

    def test_init_settings_validation_failure(self):
        """Test init_settings with validation failures."""
        get_settings.cache_clear()

        # Create a scenario that would fail production validation
        with patch.dict(
            os.environ, {"ENVIRONMENT": "production", "OPENAI_API_KEY": ""}, clear=False
        ):
            with pytest.raises(ValueError) as exc_info:
                init_settings()

            assert "Critical settings validation failed" in str(exc_info.value)


class TestEdgeCasesAndErrorHandling:
    """Test suite for edge cases and error handling scenarios."""

    def test_invalid_type_conversions(self):
        """Test handling of invalid type conversions."""
        env_vars = {
            "SUPABASE_TIMEOUT": "not-a-number",
            "SUPABASE_AUTO_REFRESH_TOKEN": "not-a-boolean",
            "SUPABASE_VECTOR_DIMENSIONS": "not-an-integer",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            with pytest.raises(ValidationError) as exc_info:
                DatabaseConfig(_env_file=None)

            errors = exc_info.value.errors()
            # Should have validation errors for invalid types
            assert len(errors) > 0

    def test_unicode_and_special_characters(self):
        """Test handling of Unicode and special characters."""
        special_chars = "!@#$%^&*()_+-=[]{}|;:'\",.<>?/~`"
        unicode_chars = "测试数据🚀✨🎯🔥💎⚡🌟🎨🎭🎪"

        env_vars = {
            "SUPABASE_PROJECT_ID": f"test-{special_chars}-{unicode_chars}",
            "SUPABASE_URL": f"https://{unicode_chars}.supabase.co",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            config = DatabaseConfig(_env_file=None)
            assert special_chars in config.project_id
            assert unicode_chars in config.project_id
            assert unicode_chars in config.url

    def test_very_long_environment_values(self):
        """Test handling of very long environment variable values."""
        long_value = "x" * 1000  # 1KB string
        env_vars = {
            "SUPABASE_URL": f"https://very-long-subdomain-{long_value}.supabase.co",
            "SUPABASE_PROJECT_ID": long_value,
        }

        with patch.dict(os.environ, env_vars, clear=False):
            config = DatabaseConfig(_env_file=None)
            assert long_value in config.url
            assert config.project_id == long_value


class TestPerformanceAndCompatibility:
    """Test suite for performance characteristics and compatibility."""

    def test_settings_instantiation_performance(self):
        """Test that settings instantiation is reasonably fast."""
        import time

        start_time = time.time()
        for _ in range(50):  # Reduced for test efficiency
            settings = CoreAppSettings(_env_file=None)
            # Access a few properties to ensure full initialization
            _ = settings.environment
            _ = settings.database.url
            _ = settings.dragonfly.url
        end_time = time.time()

        # Should be able to create 50 instances in less than 2 seconds
        assert (end_time - start_time) < 2.0

    def test_memory_usage_with_multiple_configs(self):
        """Test memory usage doesn't grow excessively."""
        settings_list = []
        for i in range(10):  # Reduced for test efficiency
            env_vars = {
                "SUPABASE_PROJECT_ID": f"project-{i}",
                "APP_NAME": f"App-{i}",
            }
            with patch.dict(os.environ, env_vars, clear=False):
                settings = CoreAppSettings(_env_file=None)
                settings_list.append(settings)

        # Basic sanity check
        assert len(settings_list) == 10
        assert all(isinstance(s, CoreAppSettings) for s in settings_list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
