"""Tests for modern flat Settings configuration."""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from tripsage_core.config import Settings, get_settings


class TestSettings:
    """Test cases for modern flat Settings class."""

    def test_default_settings(self):
        """Test default settings initialization."""
        # Test with required environment variables for flat config
        test_env = {
            "ENVIRONMENT": "development",
            "DEBUG": "false",
            "LOG_LEVEL": "INFO",
            "DATABASE_URL": "https://test-project.supabase.co",
            "DATABASE_PUBLIC_KEY": "test-anon-key",
            "DATABASE_SERVICE_KEY": "test-service-key",
            "DATABASE_JWT_SECRET": "test-jwt-secret",
            "SECRET_KEY": "test-secret-key",
            "OPENAI_API_KEY": "sk-test-openai-key",
        }

        with patch.dict(os.environ, test_env, clear=True):
            settings = Settings()

            # Core application settings
            assert settings.environment == "development"
            assert settings.debug is False
            assert settings.log_level == "INFO"
            assert settings.api_title == "TripSage API"
            assert settings.api_version == "1.0.0"

            # Database configuration (flat structure)
            assert settings.database_url == "https://test-project.supabase.co"
            assert settings.database_public_key.get_secret_value() == "test-anon-key"
            assert settings.database_service_key.get_secret_value() == "test-service-key"
            assert settings.database_jwt_secret.get_secret_value() == "test-jwt-secret"

            # Security
            assert settings.secret_key.get_secret_value() == "test-secret-key"

            # AI services
            assert settings.openai_api_key.get_secret_value() == "sk-test-openai-key"
            assert settings.openai_model == "gpt-4o"

            # Cache/Redis settings
            assert settings.redis_url is None  # Optional
            assert settings.redis_max_connections == 50

            # Rate limiting
            assert settings.rate_limit_requests == 100
            assert settings.rate_limit_window == 60

    def test_environment_validation(self):
        """Test environment field validation."""
        test_env = {
            "DATABASE_URL": "https://test.supabase.co",
            "DATABASE_PUBLIC_KEY": "test-key",
            "DATABASE_SERVICE_KEY": "test-key",
            "DATABASE_JWT_SECRET": "test-secret",
            "SECRET_KEY": "test-secret",
            "OPENAI_API_KEY": "sk-test-key",
        }

        # Valid environments
        for env in ["development", "production", "test", "testing"]:
            with patch.dict(os.environ, {**test_env, "ENVIRONMENT": env}, clear=True):
                settings = Settings()
                assert settings.environment == env

        # Invalid environment
        with patch.dict(os.environ, {**test_env, "ENVIRONMENT": "invalid"}, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings()

            errors = exc_info.value.errors()
            assert len(errors) == 1
            assert "Environment must be one of" in str(errors[0]["msg"])

    def test_environment_check_methods(self):
        """Test environment checking helper methods."""
        test_env = {
            "DATABASE_URL": "https://test.supabase.co",
            "DATABASE_PUBLIC_KEY": "test-key",
            "DATABASE_SERVICE_KEY": "test-key",
            "DATABASE_JWT_SECRET": "test-secret",
            "SECRET_KEY": "test-secret",
            "OPENAI_API_KEY": "sk-test-key",
        }

        # Development
        with patch.dict(os.environ, {**test_env, "ENVIRONMENT": "development"}, clear=True):
            settings = Settings()
            assert settings.is_development is True
            assert settings.is_production is False
            assert settings.is_testing is False

        # Production
        with patch.dict(os.environ, {**test_env, "ENVIRONMENT": "production"}, clear=True):
            settings = Settings()
            assert settings.is_development is False
            assert settings.is_production is True
            assert settings.is_testing is False

        # Testing
        with patch.dict(os.environ, {**test_env, "ENVIRONMENT": "test"}, clear=True):
            settings = Settings()
            assert settings.is_development is False
            assert settings.is_production is False
            assert settings.is_testing is True

    def test_environment_variable_loading(self):
        """Test loading settings from environment variables."""
        env_vars = {
            "ENVIRONMENT": "development",
            "DEBUG": "true",
            "LOG_LEVEL": "DEBUG",
            "DATABASE_URL": "https://staging.supabase.co",
            "DATABASE_PUBLIC_KEY": "staging-anon-key",
            "DATABASE_SERVICE_KEY": "staging-service-key",
            "DATABASE_JWT_SECRET": "my-jwt-secret",
            "SECRET_KEY": "staging-secret-key",
            "OPENAI_API_KEY": "sk-test-key-123",
            "REDIS_URL": "redis://staging:6379/1",
            "RATE_LIMIT_REQUESTS": "200",
            "RATE_LIMIT_WINDOW": "120",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()

            assert settings.environment == "development"
            assert settings.debug is True
            assert settings.log_level == "DEBUG"
            assert settings.database_url == "https://staging.supabase.co"
            assert settings.database_public_key.get_secret_value() == "staging-anon-key"
            assert settings.database_service_key.get_secret_value() == "staging-service-key"
            assert settings.database_jwt_secret.get_secret_value() == "my-jwt-secret"
            assert settings.secret_key.get_secret_value() == "staging-secret-key"
            assert settings.openai_api_key.get_secret_value() == "sk-test-key-123"
            assert settings.redis_url == "redis://staging:6379/1"
            assert settings.rate_limit_requests == 200
            assert settings.rate_limit_window == 120

    def test_get_settings_caching(self):
        """Test that get_settings returns cached instance."""
        # Clear cache first
        get_settings.cache_clear()

        test_env = {
            "ENVIRONMENT": "development",
            "DATABASE_URL": "https://test.supabase.co",
            "DATABASE_PUBLIC_KEY": "test-key",
            "DATABASE_SERVICE_KEY": "test-key",
            "DATABASE_JWT_SECRET": "test-secret",
            "SECRET_KEY": "test-secret",
            "OPENAI_API_KEY": "sk-test-key",
        }

        with patch.dict(os.environ, test_env, clear=True):
            settings1 = get_settings()
            settings2 = get_settings()

            # Should be the same instance due to lru_cache
            assert settings1 is settings2

            # Clear cache and verify new instance
            get_settings.cache_clear()
            settings3 = get_settings()
            assert settings3 is not settings1

    def test_complete_production_settings(self):
        """Test fully configured production settings."""
        env_vars = {
            "ENVIRONMENT": "production",
            "DEBUG": "false",
            "LOG_LEVEL": "INFO",
            "DATABASE_URL": "https://prod.supabase.co",
            "DATABASE_PUBLIC_KEY": "prod-anon-key",
            "DATABASE_SERVICE_KEY": "prod-service-key",
            "DATABASE_JWT_SECRET": "prod-jwt-secret",
            "SECRET_KEY": "prod-secret-key",
            "OPENAI_API_KEY": "sk-prod-openai-key",
            "REDIS_URL": "redis://prod-cache:6379/0",
            "RATE_LIMIT_REQUESTS": "1000",
            "RATE_LIMIT_WINDOW": "60",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()

            # Core settings
            assert settings.environment == "production"
            assert settings.debug is False
            assert settings.is_production is True

            # Database settings
            assert settings.database_url == "https://prod.supabase.co"
            assert settings.database_public_key.get_secret_value() == "prod-anon-key"
            assert settings.database_service_key.get_secret_value() == "prod-service-key"
            assert settings.database_jwt_secret.get_secret_value() == "prod-jwt-secret"

            # Security
            assert settings.secret_key.get_secret_value() == "prod-secret-key"

            # AI services
            assert settings.openai_api_key.get_secret_value() == "sk-prod-openai-key"

            # Cache
            assert settings.redis_url == "redis://prod-cache:6379/0"

            # Rate limiting
            assert settings.rate_limit_requests == 1000
            assert settings.rate_limit_window == 60
