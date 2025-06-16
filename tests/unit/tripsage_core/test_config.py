"""
Modern configuration testing for TripSage Core.

Tests the simplified, consolidated configuration system following 2025 best practices.
Focuses on the flat AppSettings and APISettings structure with feature toggles.
"""

import os
import tempfile
from unittest.mock import patch

import pytest
from pydantic import SecretStr, ValidationError

from tripsage_core.config import (
    APISettings,
    AppSettings,
    CoreAppSettings,  # Backward compatibility alias
    get_api_settings,
    get_settings,
    init_settings,
)


class TestAppSettings:
    """Test AppSettings main configuration class."""

    def test_app_settings_defaults(self):
        """Test default configuration values."""
        # Clear environment variables that would override defaults
        env_vars_to_clear = ["ENVIRONMENT", "DEBUG", "LOG_LEVEL", "OPENAI_API_KEY"]

        with patch.dict(os.environ, {}, clear=False):
            for var in env_vars_to_clear:
                os.environ.pop(var, None)

            # Override required field for test
            os.environ["OPENAI_API_KEY"] = "test-key-for-testing"

            settings = AppSettings(_env_file=None)

            assert settings.environment == "development"
            assert settings.debug is False
            assert settings.log_level == "INFO"

            # Database defaults
            assert settings.database_url == "https://test-project.supabase.co"
            assert settings.database_key.get_secret_value().startswith(
                "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
            )
            assert settings.database_public_key.get_secret_value().startswith(
                "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
            )

            # Redis/Cache defaults
            assert settings.redis_url == "redis://localhost:6379/0"
            assert settings.redis_password is None
            assert settings.redis_max_connections == 10000
            assert settings.cache_ttl_short == 300
            assert settings.cache_ttl_medium == 3600
            assert settings.cache_ttl_long == 86400

            # Feature flags defaults
            assert settings.enable_advanced_agents is False
            assert settings.enable_memory_system is True
            assert settings.enable_real_time is True
            assert settings.enable_vector_search is True
            assert settings.enable_monitoring is False

    def test_app_settings_environment_validation(self):
        """Test environment validation."""
        # Valid environments
        for env in ["development", "production", "test", "testing"]:
            with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
                settings = AppSettings(environment=env, _env_file=None)
                assert settings.environment == env

        # Invalid environment
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with pytest.raises(ValidationError) as exc_info:
                AppSettings(environment="invalid", _env_file=None)

            error = exc_info.value.errors()[0]
            assert (
                "Input should be 'development', 'production', 'test' or 'testing'"
                in error["msg"]
            )

    def test_app_settings_environment_methods(self):
        """Test environment checking methods."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            # Development
            dev_settings = AppSettings(environment="development", _env_file=None)
            assert dev_settings.is_development is True
            assert dev_settings.is_production is False

            # Production
            prod_settings = AppSettings(environment="production", _env_file=None)
            assert prod_settings.is_development is False
            assert prod_settings.is_production is True

    def test_app_settings_feature_flags(self):
        """Test feature flag functionality."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            settings = AppSettings(
                enable_advanced_agents=True,
                enable_memory_system=False,
                enable_monitoring=True,
                _env_file=None,
            )

            assert settings.enable_advanced_agents is True
            assert settings.enable_memory_system is False
            assert settings.enable_monitoring is True
            assert settings.enable_real_time is True  # Default
            assert settings.enable_vector_search is True  # Default

    def test_app_settings_environment_variables(self):
        """Test loading from environment variables."""
        env_vars = {
            "ENVIRONMENT": "production",
            "DEBUG": "true",
            "LOG_LEVEL": "DEBUG",
            "DATABASE_URL": "https://custom-project.supabase.co",
            "REDIS_URL": "redis://custom-redis:6380/1",
            "REDIS_PASSWORD": "custom-password",
            "REDIS_MAX_CONNECTIONS": "5000",
            "CACHE_TTL_SHORT": "600",
            "CACHE_TTL_MEDIUM": "7200",
            "CACHE_TTL_LONG": "172800",
            "OPENAI_API_KEY": "custom-openai-key",
            "OPENAI_MODEL": "gpt-4-turbo",
            "ENABLE_ADVANCED_AGENTS": "true",
            "ENABLE_MEMORY_SYSTEM": "false",
            "ENABLE_REAL_TIME": "false",
            "ENABLE_VECTOR_SEARCH": "false",
            "ENABLE_MONITORING": "true",
        }

        with patch.dict(os.environ, env_vars):
            settings = AppSettings()

            assert settings.environment == "production"
            assert settings.debug is True
            assert settings.log_level == "DEBUG"
            assert settings.database_url == "https://custom-project.supabase.co"
            assert settings.redis_url == "redis://custom-redis:6380/1"
            assert settings.redis_password == "custom-password"
            assert settings.redis_max_connections == 5000
            assert settings.cache_ttl_short == 600
            assert settings.cache_ttl_medium == 7200
            assert settings.cache_ttl_long == 172800
            assert settings.openai_api_key.get_secret_value() == "custom-openai-key"
            assert settings.openai_model == "gpt-4-turbo"
            assert settings.enable_advanced_agents is True
            assert settings.enable_memory_system is False
            assert settings.enable_real_time is False
            assert settings.enable_vector_search is False
            assert settings.enable_monitoring is True

    def test_app_settings_secret_handling(self):
        """Test proper secret handling."""
        with patch.dict(os.environ, {}):
            settings = AppSettings(
                openai_api_key=SecretStr("secret-openai-key"),
                database_key=SecretStr("secret-database-key"),
                database_public_key=SecretStr("secret-public-key"),
                database_jwt_secret=SecretStr("secret-jwt"),
                _env_file=None,
            )

            # Secrets should be properly wrapped
            assert isinstance(settings.openai_api_key, SecretStr)
            assert isinstance(settings.database_key, SecretStr)
            assert isinstance(settings.database_public_key, SecretStr)
            assert isinstance(settings.database_jwt_secret, SecretStr)

            # Should be able to get secret values
            assert settings.openai_api_key.get_secret_value() == "secret-openai-key"
            assert settings.database_key.get_secret_value() == "secret-database-key"

            # Repr should not expose secrets
            settings_repr = repr(settings)
            assert "secret-openai-key" not in settings_repr
            assert "secret-database-key" not in settings_repr


class TestAPISettings:
    """Test APISettings configuration class."""

    def test_api_settings_defaults(self):
        """Test default API configuration values."""
        with patch.dict(os.environ, {}, clear=False):
            # Clear API-prefixed environment variables
            for key in list(os.environ.keys()):
                if key.startswith("API_"):
                    os.environ.pop(key, None)

            settings = APISettings(_env_file=None)

            assert settings.title == "TripSage API"
            assert settings.version == "1.0.0"
            assert settings.prefix == "/api/v1"
            assert settings.cors_origins == [
                "http://localhost:3000",
                "http://localhost:3001",
            ]
            assert settings.cors_credentials is True
            assert settings.rate_limit_requests == 100
            assert settings.rate_limit_window == 60
            assert settings.allowed_hosts == ["*"]

    def test_api_settings_environment_variables(self):
        """Test loading API settings from environment variables."""
        env_vars = {
            "API_TITLE": "Custom TripSage API",
            "API_VERSION": "2.0.0",
            "API_PREFIX": "/api/v2",
            "API_CORS_ORIGINS": '["https://example.com", "https://app.example.com"]',
            "API_CORS_CREDENTIALS": "false",
            "API_RATE_LIMIT_REQUESTS": "200",
            "API_RATE_LIMIT_WINDOW": "120",
            "API_ALLOWED_HOSTS": '["example.com", "app.example.com"]',
        }

        with patch.dict(os.environ, env_vars):
            settings = APISettings()

            assert settings.title == "Custom TripSage API"
            assert settings.version == "2.0.0"
            assert settings.prefix == "/api/v2"
            assert settings.cors_credentials is False
            assert settings.rate_limit_requests == 200
            assert settings.rate_limit_window == 120


class TestBackwardCompatibility:
    """Test backward compatibility features."""

    def test_core_app_settings_alias(self):
        """Test that CoreAppSettings is properly aliased to AppSettings."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            settings = CoreAppSettings(environment="development", _env_file=None)

            assert isinstance(settings, AppSettings)
            assert settings.environment == "development"

    def test_init_settings_function(self):
        """Test init_settings function for backward compatibility."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            settings = init_settings()

            assert isinstance(settings, AppSettings)
            assert settings.environment in [
                "development",
                "production",
                "test",
                "testing",
            ]


class TestConfigurationLoading:
    """Test configuration loading patterns and caching."""

    def test_get_settings_caching(self):
        """Test that get_settings returns cached instance."""
        settings1 = get_settings()
        settings2 = get_settings()

        # Should be the same instance due to @lru_cache
        assert settings1 is settings2

    def test_get_api_settings_caching(self):
        """Test that get_api_settings returns cached instance."""
        settings1 = get_api_settings()
        settings2 = get_api_settings()

        # Should be the same instance due to @lru_cache
        assert settings1 is settings2

    def test_environment_variable_precedence(self):
        """Test that environment variables take precedence over defaults."""
        env_vars = {
            "ENVIRONMENT": "production",
            "DEBUG": "true",
            "LOG_LEVEL": "DEBUG",
            "DATABASE_URL": "https://custom.supabase.co",
            "REDIS_URL": "redis://custom:6379/0",
            "OPENAI_API_KEY": "custom-openai-key",
            "ENABLE_ADVANCED_AGENTS": "true",
        }

        with patch.dict(os.environ, env_vars):
            settings = AppSettings(_env_file=None)

            assert settings.environment == "production"
            assert settings.debug is True
            assert settings.log_level == "DEBUG"
            assert settings.database_url == "https://custom.supabase.co"
            assert settings.redis_url == "redis://custom:6379/0"
            assert settings.openai_api_key.get_secret_value() == "custom-openai-key"
            assert settings.enable_advanced_agents is True

    def test_env_file_loading(self):
        """Test loading configuration from .env file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("ENVIRONMENT=test\n")
            f.write("DATABASE_URL=https://env-file.supabase.co\n")
            f.write("OPENAI_API_KEY=env-file-openai-key\n")
            f.write("ENABLE_ADVANCED_AGENTS=true\n")
            f.flush()

            # Clear environment first to avoid conflicts
            with patch.dict(os.environ, {}, clear=False):
                for key in list(os.environ.keys()):
                    if key in [
                        "ENVIRONMENT",
                        "DATABASE_URL",
                        "OPENAI_API_KEY",
                        "ENABLE_ADVANCED_AGENTS",
                    ]:
                        os.environ.pop(key, None)

                # Create config with custom env file
                settings = AppSettings(_env_file=f.name)

                assert settings.environment == "test"
                assert settings.database_url == "https://env-file.supabase.co"
                assert (
                    settings.openai_api_key.get_secret_value() == "env-file-openai-key"
                )
                assert settings.enable_advanced_agents is True

        # Clean up
        os.unlink(f.name)


class TestConfigurationErrorHandling:
    """Test error handling and edge cases in configuration."""

    def test_invalid_environment_value(self):
        """Test handling of invalid environment values."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with pytest.raises(ValidationError) as exc_info:
                AppSettings(environment="invalid_env", _env_file=None)

            error = exc_info.value.errors()[0]
            assert (
                "Input should be 'development', 'production', 'test' or 'testing'"
                in error["msg"]
            )

    def test_missing_required_fields(self):
        """Test handling of missing required fields."""
        with patch.dict(os.environ, {}, clear=True):
            # Don't provide OPENAI_API_KEY
            with pytest.raises(ValidationError) as exc_info:
                AppSettings(_env_file=None)

            errors = exc_info.value.errors()
            assert any(error["loc"] == ("openai_api_key",) for error in errors)

    def test_configuration_with_none_values(self):
        """Test configuration with None values for optional fields."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            settings = AppSettings(redis_password=None, _env_file=None)

            assert settings.redis_password is None

    def test_model_config_validation(self):
        """Test model configuration settings."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            settings = AppSettings(_env_file=None)

            # Check model config is properly set
            assert settings.model_config["case_sensitive"] is False
            assert settings.model_config["extra"] == "ignore"
            assert settings.model_config["validate_default"] is True


class TestFeatureTogglePatterns:
    """Test feature toggle and configurable complexity patterns."""

    def test_enterprise_vs_simple_mode(self):
        """Test enterprise vs simple mode feature patterns."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            # Simple mode (default)
            simple_settings = AppSettings(
                enable_advanced_agents=False, enable_monitoring=False, _env_file=None
            )

            assert simple_settings.enable_advanced_agents is False
            assert simple_settings.enable_monitoring is False
            assert simple_settings.enable_memory_system is True  # Core feature
            assert simple_settings.enable_real_time is True  # Core feature

            # Enterprise mode
            enterprise_settings = AppSettings(
                enable_advanced_agents=True,
                enable_monitoring=True,
                enable_memory_system=True,
                enable_real_time=True,
                enable_vector_search=True,
                _env_file=None,
            )

            assert enterprise_settings.enable_advanced_agents is True
            assert enterprise_settings.enable_monitoring is True
            assert enterprise_settings.enable_memory_system is True
            assert enterprise_settings.enable_real_time is True
            assert enterprise_settings.enable_vector_search is True

    def test_configurable_complexity_environment_based(self):
        """Test environment-based feature complexity."""
        # Development - enable all features for testing
        with patch.dict(
            os.environ,
            {
                "ENVIRONMENT": "development",
                "OPENAI_API_KEY": "test-key",
                "ENABLE_ADVANCED_AGENTS": "true",
                "ENABLE_MONITORING": "true",
            },
        ):
            dev_settings = AppSettings()
            assert dev_settings.enable_advanced_agents is True
            assert dev_settings.enable_monitoring is True

        # Production - minimal features for stability
        with patch.dict(
            os.environ,
            {
                "ENVIRONMENT": "production",
                "OPENAI_API_KEY": "test-key",
                "ENABLE_ADVANCED_AGENTS": "false",
                "ENABLE_MONITORING": "false",
            },
        ):
            prod_settings = AppSettings()
            assert prod_settings.enable_advanced_agents is False
            assert prod_settings.enable_monitoring is False
            # Core features still enabled
            assert prod_settings.enable_memory_system is True
            assert prod_settings.enable_real_time is True


class TestModernBestPractices:
    """Test that the config follows 2025 best practices."""

    def test_flat_configuration_structure(self):
        """Test that configuration is flat, not nested."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            settings = AppSettings(_env_file=None)

            # All settings should be directly accessible (flat structure)
            assert hasattr(settings, "database_url")
            assert hasattr(settings, "redis_url")
            assert hasattr(settings, "openai_api_key")
            assert hasattr(settings, "enable_advanced_agents")

            # No nested config objects
            assert not hasattr(settings, "database")
            assert not hasattr(settings, "dragonfly")
            assert not hasattr(settings, "langgraph")

    def test_pydantic_settings_patterns(self):
        """Test modern Pydantic Settings patterns."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            settings = AppSettings(_env_file=None)

            # Uses BaseSettings
            from pydantic_settings import BaseSettings

            assert isinstance(settings, BaseSettings)

            # Has proper SettingsConfigDict
            assert hasattr(settings, "model_config")
            assert settings.model_config["env_file"] == ".env"
            assert settings.model_config["case_sensitive"] is False

    def test_configurable_complexity_toggles(self):
        """Test configurable complexity feature toggles."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            settings = AppSettings(_env_file=None)

            # Should have clear feature toggles for complexity levels
            complexity_toggles = [
                "enable_advanced_agents",
                "enable_memory_system",
                "enable_real_time",
                "enable_vector_search",
                "enable_monitoring",
            ]

            for toggle in complexity_toggles:
                assert hasattr(settings, toggle)
                assert isinstance(getattr(settings, toggle), bool)
