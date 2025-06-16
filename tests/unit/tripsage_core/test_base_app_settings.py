"""Tests for base_app_settings module."""

import os
from unittest.mock import patch

import pytest
from pydantic import SecretStr, ValidationError

from tripsage_core.config import CoreAppSettings, get_settings


class TestCoreAppSettings:
    """Test cases for CoreAppSettings class."""

    def test_default_settings(self):
        """Test default settings initialization."""
        # Test with clean environment to verify defaults
        clean_env = {
            "ENVIRONMENT": "development",
            "DEBUG": "false",
            "LOG_LEVEL": "INFO",
        }

        with patch.dict(os.environ, clean_env, clear=True):
            settings = CoreAppSettings(_env_file=None)

            # Application metadata
            assert settings.app_name == "TripSage"
            assert settings.environment == "development"
            assert settings.debug is False
            assert settings.log_level == "INFO"

            # Database connections - defaults
            assert settings.database.supabase_url == "https://test-project.supabase.co"
            assert (
                settings.database.supabase_anon_key.get_secret_value()
                == "test-anon-key"
            )
            assert settings.database.supabase_service_role_key is None
            assert settings.dragonfly.url == "redis://localhost:6379/0"

            # External services - defaults
            assert settings.openai_api_key.get_secret_value() == "test-openai-key"
            assert settings.google_maps_api_key is None
            assert settings.crawl4ai.api_url == "http://localhost:8000/api"

            # Feature flags
            assert settings.feature_flags.enable_agent_memory is True
            assert settings.feature_flags.enable_caching is True

    def test_environment_validation(self):
        """Test environment field validation."""
        # Valid environments
        for env in ["development", "testing", "staging", "production"]:
            settings = CoreAppSettings(_env_file=None, environment=env)
            assert settings.environment == env

        # Invalid environment
        with pytest.raises(ValidationError) as exc_info:
            CoreAppSettings(_env_file=None, environment="invalid")

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "Environment must be one of" in str(errors[0]["ctx"]["error"])

    def test_log_level_validation(self):
        """Test log level validation and normalization."""
        # Valid log levels (case insensitive)
        for level in ["debug", "INFO", "Warning", "ERROR", "CRITICAL"]:
            settings = CoreAppSettings(_env_file=None, log_level=level)
            assert settings.log_level == level.upper()

        # Invalid log level
        with pytest.raises(ValidationError) as exc_info:
            CoreAppSettings(_env_file=None, log_level="INVALID")

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "Log level must be one of" in str(errors[0]["ctx"]["error"])

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

    def test_get_secret_value(self):
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

    def test_validate_critical_settings(self):
        """Test critical settings validation."""
        # Valid development settings
        settings = CoreAppSettings(_env_file=None, environment="development")
        errors = settings.validate_critical_settings()
        assert errors == []

        # Missing critical settings - create with environment variables
        with patch.dict(
            os.environ,
            {"OPENAI_API_KEY": "", "DATABASE__SUPABASE_ANON_KEY": ""},
            clear=False,
        ):
            settings = CoreAppSettings(_env_file=None)
            errors = settings.validate_critical_settings()
            assert "OpenAI API key is missing" in errors
            assert "Supabase anonymous key is missing" in errors

    def test_production_validation(self):
        """Test production-specific validations."""
        # Production with debug enabled
        settings = CoreAppSettings(_env_file=None, environment="production", debug=True)
        errors = settings.validate_critical_settings()
        assert "Debug mode should be disabled in production" in errors

        # Production with default secrets
        settings = CoreAppSettings(
            _env_file=None,
            environment="production",
            debug=False,
            api_key_master_secret=SecretStr("master-secret-for-byok-encryption"),
        )
        errors = settings.validate_critical_settings()
        # Note: JWT secret key validation was removed in favor of Supabase JWT
        assert "API key master secret must be changed in production" in errors

    def test_nested_configurations(self):
        """Test nested configuration objects."""
        settings = CoreAppSettings(_env_file=None)

        # Database config
        assert hasattr(settings.database, "supabase_url")
        assert hasattr(settings.database, "pgvector_enabled")

        # Dragonfly config
        assert hasattr(settings.dragonfly, "url")
        assert hasattr(settings.dragonfly, "ttl_short")

        # Agent config
        assert hasattr(settings.agent, "model_name")
        assert hasattr(settings.agent, "max_tokens")

        # Feature flags
        assert hasattr(settings.feature_flags, "enable_agent_memory")
        assert hasattr(settings.feature_flags, "enable_caching")

    def test_environment_variable_loading(self):
        """Test loading settings from environment variables."""
        env_vars = {
            "APP_NAME": "TestApp",
            "ENVIRONMENT": "staging",
            "DEBUG": "true",
            "LOG_LEVEL": "DEBUG",
            "OPENAI_API_KEY": "test-key-123",
            "DATABASE__SUPABASE_JWT_SECRET": "my-jwt-secret",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            settings = CoreAppSettings(_env_file=None)

            assert settings.app_name == "TestApp"
            assert settings.environment == "staging"
            assert settings.debug is True
            assert settings.log_level == "DEBUG"
            assert settings.openai_api_key.get_secret_value() == "test-key-123"
            assert (
                settings.database.supabase_jwt_secret.get_secret_value()
                == "my-jwt-secret"
            )

    def test_get_settings_caching(self):
        """Test that get_settings returns cached instance."""
        # Clear cache first
        get_settings.cache_clear()

        # Test with clean environment
        with patch.dict(os.environ, {}, clear=True):
            settings1 = get_settings()
            settings2 = get_settings()

            # Should be the same instance due to lru_cache
            assert settings1 is settings2

            # Clear cache and verify new instance
            get_settings.cache_clear()
            settings3 = get_settings()
            assert settings3 is not settings1

    def test_feature_flags(self):
        """Test feature flags configuration."""
        settings = CoreAppSettings(_env_file=None)

        # Default feature flags
        assert settings.feature_flags.enable_agent_memory is True
        assert settings.feature_flags.enable_parallel_agents is True
        assert settings.feature_flags.enable_streaming_responses is True
        assert settings.feature_flags.enable_rate_limiting is True
        assert settings.feature_flags.enable_caching is True
        assert settings.feature_flags.enable_debug_mode is False

    def test_complete_production_settings(self):
        """Test fully configured production settings."""
        env_vars = {
            "ENVIRONMENT": "production",
            "DEBUG": "false",
            "API_KEY_MASTER_SECRET": "prod-master-secret",
            "OPENAI_API_KEY": "prod-openai-key",
            "GOOGLE_MAPS_API_KEY": "prod-google-key",
            "DUFFEL_API_KEY": "prod-duffel-key",
            "OPENWEATHERMAP_API_KEY": "prod-weather-key",
            "DATABASE__SUPABASE_URL": "https://prod.supabase.co",
            "DATABASE__SUPABASE_ANON_KEY": "prod-anon-key",
            "DATABASE__SUPABASE_JWT_SECRET": "prod-jwt-secret",
            "DRAGONFLY__URL": "redis://prod-cache:6379/0",
            "CRAWL4AI__API_URL": "https://crawl4ai.prod/api",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            settings = CoreAppSettings(_env_file=None)

            # Should have no validation errors
            errors = settings.validate_critical_settings()
            assert errors == []

            # All secrets should be accessible
            assert settings.get_secret_value("openai_api_key") == "prod-openai-key"
            assert settings.get_secret_value("google_maps_api_key") == "prod-google-key"
            assert settings.get_secret_value("duffel_api_key") == "prod-duffel-key"
            assert (
                settings.database.supabase_jwt_secret.get_secret_value()
                == "prod-jwt-secret"
            )
