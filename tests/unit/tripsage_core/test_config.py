"""
Modern configuration testing for TripSage Core.

Tests the simplified, consolidated configuration system following 2025 best practices.
Focuses on the unified Settings structure with feature toggles.
"""

import os
import tempfile
from unittest.mock import patch

import pytest
from pydantic import SecretStr, ValidationError

from tripsage_core.config import (
    Settings,
    get_settings,
)


class TestSettings:
    """Test unified Settings configuration class."""

    def test_settings_defaults(self):
        """Test default configuration values."""
        # Clear environment variables that would override defaults
        env_vars_to_clear = ["ENVIRONMENT", "DEBUG", "LOG_LEVEL", "OPENAI_API_KEY"]

        with patch.dict(os.environ, {}, clear=False):
            for var in env_vars_to_clear:
                os.environ.pop(var, None)

            # Override required fields for test
            os.environ.update(
                {
                    "OPENAI_API_KEY": "test-key-for-testing",
                    "DATABASE_URL": "https://test-project.supabase.co",
                    "DATABASE_PUBLIC_KEY": "test-public-key",
                    "DATABASE_SERVICE_KEY": "test-service-key",
                }
            )

            settings = Settings(_env_file=None)

            assert settings.environment == "development"
            assert settings.debug is False
            assert settings.log_level == "INFO"
            assert settings.api_title == "TripSage API"
            assert settings.api_version == "1.0.0"

    def test_settings_environment_validation(self):
        """Test environment validation."""
        # Valid environments
        for env in ["development", "production", "test", "testing"]:
            with patch.dict(
                os.environ,
                {
                    "OPENAI_API_KEY": "test-key",
                    "DATABASE_URL": "https://test.supabase.co",
                    "DATABASE_PUBLIC_KEY": "test-public-key",
                    "DATABASE_SERVICE_KEY": "test-service-key",
                },
            ):
                settings = Settings(environment=env, _env_file=None)
                assert settings.environment == env

        # Invalid environment
        with patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY": "test-key",
                "DATABASE_URL": "https://test.supabase.co",
                "DATABASE_PUBLIC_KEY": "test-public-key",
                "DATABASE_SERVICE_KEY": "test-service-key",
            },
        ):
            with pytest.raises(ValidationError) as exc_info:
                Settings(environment="invalid", _env_file=None)

            error = exc_info.value.errors()[0]
            assert "Input should be" in error["msg"]

    def test_settings_environment_variables(self):
        """Test loading from environment variables."""
        env_vars = {
            "ENVIRONMENT": "production",
            "DEBUG": "true",
            "LOG_LEVEL": "DEBUG",
            "DATABASE_URL": "https://custom-project.supabase.co",
            "DATABASE_PUBLIC_KEY": "custom-public-key",
            "DATABASE_SERVICE_KEY": "custom-service-key",
            "OPENAI_API_KEY": "custom-openai-key",
            "API_TITLE": "Custom TripSage API",
            "API_VERSION": "2.0.0",
        }

        with patch.dict(os.environ, env_vars):
            settings = Settings()

            assert settings.environment == "production"
            assert settings.debug is True
            assert settings.log_level == "DEBUG"
            assert settings.database_url == "https://custom-project.supabase.co"
            assert settings.openai_api_key.get_secret_value() == "custom-openai-key"
            assert settings.api_title == "Custom TripSage API"
            assert settings.api_version == "2.0.0"

    def test_settings_secret_handling(self):
        """Test proper secret handling."""
        with patch.dict(os.environ, {}):
            settings = Settings(
                openai_api_key=SecretStr("secret-openai-key"),
                database_url="https://test.supabase.co",
                database_public_key=SecretStr("secret-public-key"),
                database_service_key=SecretStr("secret-service-key"),
                _env_file=None,
            )

            # Secrets should be properly wrapped
            assert isinstance(settings.openai_api_key, SecretStr)
            assert isinstance(settings.database_public_key, SecretStr)
            assert isinstance(settings.database_service_key, SecretStr)

            # Should be able to get secret values
            assert settings.openai_api_key.get_secret_value() == "secret-openai-key"
            assert (
                settings.database_public_key.get_secret_value() == "secret-public-key"
            )

            # Repr should not expose secrets
            settings_repr = repr(settings)
            assert "secret-openai-key" not in settings_repr
            assert "secret-public-key" not in settings_repr


class TestConfigurationLoading:
    """Test configuration loading patterns and caching."""

    def test_get_settings_caching(self):
        """Test that get_settings returns cached instance."""
        settings1 = get_settings()
        settings2 = get_settings()

        # Should be the same instance due to @lru_cache
        assert settings1 is settings2

    def test_environment_variable_precedence(self):
        """Test that environment variables take precedence over defaults."""
        env_vars = {
            "ENVIRONMENT": "production",
            "DEBUG": "true",
            "LOG_LEVEL": "DEBUG",
            "DATABASE_URL": "https://custom.supabase.co",
            "DATABASE_PUBLIC_KEY": "custom-public-key",
            "DATABASE_SERVICE_KEY": "custom-service-key",
            "OPENAI_API_KEY": "custom-openai-key",
        }

        with patch.dict(os.environ, env_vars):
            settings = Settings(_env_file=None)

            assert settings.environment == "production"
            assert settings.debug is True
            assert settings.log_level == "DEBUG"
            assert settings.database_url == "https://custom.supabase.co"
            assert settings.openai_api_key.get_secret_value() == "custom-openai-key"

    def test_env_file_loading(self):
        """Test loading configuration from .env file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("ENVIRONMENT=test\n")
            f.write("DATABASE_URL=https://env-file.supabase.co\n")
            f.write("DATABASE_PUBLIC_KEY=env-file-public-key\n")
            f.write("DATABASE_SERVICE_KEY=env-file-service-key\n")
            f.write("OPENAI_API_KEY=env-file-openai-key\n")
            f.flush()

            # Clear environment first to avoid conflicts
            with patch.dict(os.environ, {}, clear=False):
                for key in list(os.environ.keys()):
                    if key in [
                        "ENVIRONMENT",
                        "DATABASE_URL",
                        "DATABASE_PUBLIC_KEY",
                        "DATABASE_SERVICE_KEY",
                        "OPENAI_API_KEY",
                    ]:
                        os.environ.pop(key, None)

                # Create config with custom env file
                settings = Settings(_env_file=f.name)

                assert settings.environment == "test"
                assert settings.database_url == "https://env-file.supabase.co"
                assert (
                    settings.openai_api_key.get_secret_value() == "env-file-openai-key"
                )

        # Clean up
        os.unlink(f.name)


class TestConfigurationErrorHandling:
    """Test error handling and edge cases in configuration."""

    def test_invalid_environment_value(self):
        """Test handling of invalid environment values."""
        with patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY": "test-key",
                "DATABASE_URL": "https://test.supabase.co",
                "DATABASE_PUBLIC_KEY": "test-public-key",
                "DATABASE_SERVICE_KEY": "test-service-key",
            },
        ):
            with pytest.raises(ValidationError) as exc_info:
                Settings(environment="invalid_env", _env_file=None)

            error = exc_info.value.errors()[0]
            assert "Input should be" in error["msg"]

    def test_missing_required_fields(self):
        """Test handling of missing required fields."""
        with patch.dict(os.environ, {}, clear=True):
            # Don't provide required fields
            with pytest.raises(ValidationError) as exc_info:
                Settings(_env_file=None)

            errors = exc_info.value.errors()
            required_fields = [
                error["loc"][0] for error in errors if error["type"] == "missing"
            ]

            # Should require these critical fields
            assert "openai_api_key" in required_fields
            assert "database_url" in required_fields


class TestModernBestPractices:
    """Test that the config follows 2025 best practices."""

    def test_flat_configuration_structure(self):
        """Test that configuration is flat, not nested."""
        with patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY": "test-key",
                "DATABASE_URL": "https://test.supabase.co",
                "DATABASE_PUBLIC_KEY": "test-public-key",
                "DATABASE_SERVICE_KEY": "test-service-key",
            },
        ):
            settings = Settings(_env_file=None)

            # All settings should be directly accessible (flat structure)
            assert hasattr(settings, "database_url")
            assert hasattr(settings, "openai_api_key")
            assert hasattr(settings, "api_title")
            assert hasattr(settings, "cors_origins")

            # No nested config objects - should be flat
            assert not hasattr(settings, "database")
            assert not hasattr(settings, "api")

    def test_pydantic_settings_patterns(self):
        """Test modern Pydantic Settings patterns."""
        with patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY": "test-key",
                "DATABASE_URL": "https://test.supabase.co",
                "DATABASE_PUBLIC_KEY": "test-public-key",
                "DATABASE_SERVICE_KEY": "test-service-key",
            },
        ):
            settings = Settings(_env_file=None)

            # Uses BaseSettings
            from pydantic_settings import BaseSettings

            assert isinstance(settings, BaseSettings)

            # Has proper SettingsConfigDict
            assert hasattr(settings, "model_config")
            assert settings.model_config["env_file"] == ".env"
            assert settings.model_config["case_sensitive"] is False

    def test_unified_configuration(self):
        """Test that API and app settings are unified in one class."""
        with patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY": "test-key",
                "DATABASE_URL": "https://test.supabase.co",
                "DATABASE_PUBLIC_KEY": "test-public-key",
                "DATABASE_SERVICE_KEY": "test-service-key",
            },
        ):
            settings = Settings(_env_file=None)

            # Should have both API and app configuration in one place
            assert hasattr(settings, "database_url")  # App config
            assert hasattr(settings, "api_title")  # API config
            assert hasattr(settings, "cors_origins")  # API config
            assert hasattr(settings, "environment")  # App config
