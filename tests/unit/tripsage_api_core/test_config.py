"""Updated test suite for tripsage.api.core.config module.

This module provides tests for the unified API configuration system,
updated for the removal of JWT settings and modernized for Pydantic v2.
"""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from tripsage.api.core.config import Settings, get_settings


class TestSettings:
    """Test the unified Settings configuration class."""

    def test_settings_inheritance(self):
        """Test that Settings properly inherits from Settings."""
        settings = Settings()

        # Should have Settings attributes
        assert hasattr(settings, "app_name")
        assert hasattr(settings, "environment")
        assert hasattr(settings, "openai_api_key")

        # Should have API-specific attributes
        assert hasattr(settings, "api_prefix")
        assert hasattr(settings, "cors_origins")
        assert hasattr(settings, "rate_limit_enabled")
        assert hasattr(settings, "enable_byok")

        # JWT settings should NOT be present (removed for Supabase Auth)
        assert not hasattr(settings, "jwt_secret_key")
        assert not hasattr(settings, "access_token_expire_minutes")
        assert not hasattr(settings, "jwt_algorithm")

    def test_default_values(self):
        """Test that all default values are set correctly."""
        settings = Settings()

        # API Configuration
        assert settings.api_prefix == "/api/v1"
        assert settings.api_title == "TripSage API"
        assert settings.api_version == "1.0.0"
        assert settings.api_description == "TripSage AI Travel Planning API"

        # CORS Settings
        expected_origins = [
            "http://localhost:3000",
            "http://localhost:3001",
            "https://tripsage.app",
            "https://app.tripsage.ai",
        ]
        assert settings.cors_origins == expected_origins
        assert settings.cors_allow_credentials is True
        assert "GET" in settings.cors_allow_methods
        assert "POST" in settings.cors_allow_methods

        # Rate Limiting
        assert settings.rate_limit_enabled is True
        assert settings.rate_limit_requests == 100
        assert settings.rate_limit_window == 60
        assert settings.rate_limit_authenticated_requests == 1000

        # BYOK Settings
        assert settings.enable_byok is True
        expected_services = [
            "openai",
            "google_maps",
            "duffel",
            "openweathermap",
            "firecrawl",
        ]
        assert set(settings.byok_services) == set(expected_services)
        assert settings.byok_encryption_enabled is True

    def test_environment_variable_loading(self):
        """Test loading configuration from environment variables."""
        with patch.dict(
            os.environ,
            {
                "TRIPSAGE_API_API_PREFIX": "/api/v2",
                "TRIPSAGE_API_RATE_LIMIT_REQUESTS": "200",
                "TRIPSAGE_API_ENABLE_BYOK": "false",
            },
        ):
            settings = Settings()

            assert settings.api_prefix == "/api/v2"
            assert settings.rate_limit_requests == 200
            assert settings.enable_byok is False

    def test_cors_origins_validation_development(self):
        """Test CORS origins validation in development environment."""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            # Should allow wildcard in development
            settings = Settings(cors_origins=["*"])
            assert settings.cors_origins == ["*"]

    def test_cors_origins_validation_production(self):
        """Test CORS origins validation in production environment."""
        with pytest.raises(
            ValidationError, match="Wildcard CORS origin not allowed in production"
        ):
            Settings(environment="production", cors_origins=["*"])

    def test_valid_cors_origins_production(self):
        """Test that specific origins are allowed in production."""
        settings = Settings(
            environment="production",
            cors_origins=["https://tripsage.app", "https://api.tripsage.ai"],
        )
        assert "https://tripsage.app" in settings.cors_origins
        assert "https://api.tripsage.ai" in settings.cors_origins

    def test_byok_services_validation_valid(self):
        """Test BYOK services validation with valid services."""
        valid_services = ["openai", "google_maps", "duffel"]
        settings = Settings(byok_services=valid_services)
        assert settings.byok_services == valid_services

    def test_byok_services_validation_invalid(self):
        """Test BYOK services validation with invalid service."""
        with pytest.raises(
            ValidationError, match="Unknown BYOK service: invalid_service"
        ):
            Settings(byok_services=["openai", "invalid_service"])

    def test_get_cors_config(self):
        """Test CORS configuration dictionary generation."""
        settings = Settings()
        cors_config = settings.get_cors_config()

        expected_keys = {
            "allow_origins",
            "allow_credentials",
            "allow_methods",
            "allow_headers",
        }
        assert set(cors_config.keys()) == expected_keys

        assert cors_config["allow_origins"] == settings.cors_origins
        assert cors_config["allow_credentials"] == settings.cors_allow_credentials
        assert cors_config["allow_methods"] == settings.cors_allow_methods
        assert cors_config["allow_headers"] == settings.cors_allow_headers

    def test_is_byok_service_enabled_when_enabled(self):
        """Test BYOK service check when BYOK is enabled."""
        settings = Settings(enable_byok=True, byok_services=["openai", "google_maps"])

        assert settings.is_byok_service_enabled("openai") is True
        assert settings.is_byok_service_enabled("google_maps") is True
        assert settings.is_byok_service_enabled("duffel") is False

    def test_is_byok_service_enabled_when_disabled(self):
        """Test BYOK service check when BYOK is disabled."""
        settings = Settings(enable_byok=False, byok_services=["openai"])

        assert settings.is_byok_service_enabled("openai") is False

    def test_get_rate_limit_for_endpoint_enabled(self):
        """Test rate limit retrieval when rate limiting is enabled."""
        settings = Settings(
            rate_limit_enabled=True,
            rate_limit_requests=100,
            rate_limit_authenticated_requests=500,
            rate_limit_chat_requests=50,
            rate_limit_search_requests=200,
        )

        assert settings.get_rate_limit_for_endpoint("general") == 100
        assert settings.get_rate_limit_for_endpoint("authenticated") == 500
        assert settings.get_rate_limit_for_endpoint("chat") == 50
        assert settings.get_rate_limit_for_endpoint("search") == 200
        assert settings.get_rate_limit_for_endpoint("unknown") == 100  # fallback

    def test_get_rate_limit_for_endpoint_disabled(self):
        """Test rate limit retrieval when rate limiting is disabled."""
        settings = Settings(rate_limit_enabled=False)

        assert settings.get_rate_limit_for_endpoint("general") == 0
        assert settings.get_rate_limit_for_endpoint("authenticated") == 0
        assert settings.get_rate_limit_for_endpoint("chat") == 0

    def test_env_prefix_configuration(self):
        """Test that environment variable prefix is correctly configured."""
        settings = Settings()
        assert settings.model_config["env_prefix"] == "TRIPSAGE_API_"

    def test_file_upload_configuration(self):
        """Test file upload configuration settings."""
        settings = Settings()

        assert settings.max_file_size == 52428800  # 50MB
        assert "image/jpeg" in settings.allowed_file_types
        assert "application/pdf" in settings.allowed_file_types
        assert "text/csv" in settings.allowed_file_types

    def test_websocket_configuration(self):
        """Test WebSocket configuration settings."""
        settings = Settings()

        assert settings.websocket_max_connections == 1000
        assert settings.websocket_heartbeat_interval == 30

    def test_api_key_management_configuration(self):
        """Test API key management settings."""
        settings = Settings()

        assert settings.api_key_expiration_days == 365
        assert settings.api_key_max_per_user == 10

    def test_request_configuration(self):
        """Test request/response configuration settings."""
        settings = Settings()

        assert settings.request_timeout == 30
        assert settings.max_request_size == 10485760  # 10MB


class TestGetSettings:
    """Test the get_settings function and caching behavior."""

    def test_get_settings_returns_settings_instance(self):
        """Test that get_settings returns a Settings instance."""
        settings = get_settings()
        assert isinstance(settings, Settings)

    def test_get_settings_caching(self):
        """Test that get_settings returns the same cached instance."""
        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2  # Same object reference

    def test_get_settings_cache_invalidation(self):
        """Test cache behavior with different environment variables."""
        # Clear the cache first
        get_settings.cache_clear()

        with patch.dict(os.environ, {"TRIPSAGE_API_API_PREFIX": "/api/test"}):
            settings1 = get_settings()
            assert settings1.api_prefix == "/api/test"

        # Cache should still return the same instance even with different env
        settings2 = get_settings()
        assert settings1 is settings2


class TestSettingsValidation:
    """Test advanced validation scenarios and edge cases."""

    def test_empty_cors_origins(self):
        """Test behavior with empty CORS origins list."""
        settings = Settings(cors_origins=[])
        assert settings.cors_origins == []

    def test_empty_byok_services(self):
        """Test behavior with empty BYOK services list."""
        settings = Settings(byok_services=[])
        assert settings.byok_services == []
        assert settings.is_byok_service_enabled("openai") is False

    def test_duplicate_cors_origins(self):
        """Test behavior with duplicate CORS origins."""
        origins = ["http://localhost:3000", "http://localhost:3000"]
        settings = Settings(cors_origins=origins)
        assert settings.cors_origins == origins  # Pydantic doesn't deduplicate

    def test_case_sensitivity_disabled(self):
        """Test that case sensitivity is disabled in model config."""
        assert Settings.model_config["case_sensitive"] is False

    def test_extra_fields_ignored(self):
        """Test that extra fields are ignored."""
        assert Settings.model_config["extra"] == "ignore"

    def test_validate_default_enabled(self):
        """Test that default validation is enabled."""
        assert Settings.model_config["validate_default"] is True

    def test_cors_methods_configuration(self):
        """Test CORS methods configuration."""
        settings = Settings()

        expected_methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
        assert set(settings.cors_allow_methods) == set(expected_methods)

    def test_cors_headers_configuration(self):
        """Test CORS headers configuration."""
        settings = Settings()
        assert settings.cors_allow_headers == ["*"]

    def test_rate_limiting_configuration_consistency(self):
        """Test that rate limiting configuration is internally consistent."""
        settings = Settings()

        # Authenticated limits should be higher than general limits
        assert settings.rate_limit_authenticated_requests > settings.rate_limit_requests

        # Chat limits should be reasonable for real-time communication
        assert settings.rate_limit_chat_requests <= settings.rate_limit_requests


class TestEnvironmentSpecificBehavior:
    """Test environment-specific configuration behavior."""

    def test_development_environment_defaults(self):
        """Test defaults appropriate for development environment."""
        settings = Settings(environment="development")

        # Should be configured for local development
        assert "http://localhost:3000" in settings.cors_origins
        assert settings.cors_allow_credentials is True

    def test_production_environment_security(self):
        """Test security-focused defaults for production."""
        settings = Settings(environment="production")

        # BYOK should be enabled for security
        assert settings.enable_byok is True
        assert settings.byok_encryption_enabled is True

        # Rate limiting should be enabled
        assert settings.rate_limit_enabled is True

    def test_testing_environment_configuration(self):
        """Test configuration appropriate for testing."""
        settings = Settings(environment="testing")

        # Should allow testing-specific configuration
        assert settings.environment == "testing"
        # Other settings should use reasonable defaults
        assert settings.rate_limit_enabled is True


class TestConfigurationIntegration:
    """Test integration scenarios and complex configurations."""

    def test_full_configuration_from_env(self):
        """Test loading a complete configuration from environment variables."""
        env_vars = {
            "TRIPSAGE_API_API_PREFIX": "/api/v2",
            "TRIPSAGE_API_RATE_LIMIT_REQUESTS": "150",
            "TRIPSAGE_API_ENABLE_BYOK": "true",
            "TRIPSAGE_API_BYOK_ENCRYPTION_ENABLED": "true",
            "TRIPSAGE_API_API_KEY_EXPIRATION_DAYS": "730",
        }

        with patch.dict(os.environ, env_vars):
            settings = Settings()

            assert settings.api_prefix == "/api/v2"
            assert settings.rate_limit_requests == 150
            assert settings.enable_byok is True
            assert settings.byok_encryption_enabled is True
            assert settings.api_key_expiration_days == 730

    def test_mixed_environment_and_direct_assignment(self):
        """Test mixing environment variables with direct assignment."""
        with patch.dict(os.environ, {"TRIPSAGE_API_API_PREFIX": "/api/env"}):
            # Direct assignment should override environment
            settings = Settings(api_prefix="/api/direct")
            assert settings.api_prefix == "/api/direct"

    def test_complex_cors_configuration(self):
        """Test complex CORS configuration scenarios."""
        complex_origins = [
            "https://app.tripsage.ai",
            "https://admin.tripsage.ai",
            "https://api.partner1.com",
            "https://dashboard.partner2.net",
        ]

        settings = Settings(
            cors_origins=complex_origins,
            cors_allow_methods=["GET", "POST", "PUT"],
            cors_allow_headers=["Authorization", "Content-Type", "X-API-Key"],
        )

        cors_config = settings.get_cors_config()
        assert cors_config["allow_origins"] == complex_origins
        assert set(cors_config["allow_methods"]) == {"GET", "POST", "PUT"}
        assert "Authorization" in cors_config["allow_headers"]

    def test_byok_service_management(self):
        """Test BYOK service management scenarios."""
        # Test with subset of services
        limited_services = ["openai", "google_maps"]
        settings = Settings(byok_services=limited_services)

        assert settings.is_byok_service_enabled("openai") is True
        assert settings.is_byok_service_enabled("google_maps") is True
        assert settings.is_byok_service_enabled("duffel") is False
        assert settings.is_byok_service_enabled("openweathermap") is False

    def test_rate_limiting_scenarios(self):
        """Test various rate limiting scenarios."""
        # Test disabled rate limiting
        settings_disabled = Settings(rate_limit_enabled=False)
        assert settings_disabled.get_rate_limit_for_endpoint("any") == 0

        # Test custom rate limits
        settings_custom = Settings(
            rate_limit_enabled=True,
            rate_limit_requests=50,
            rate_limit_chat_requests=25,
            rate_limit_search_requests=100,
        )

        assert settings_custom.get_rate_limit_for_endpoint("general") == 50
        assert settings_custom.get_rate_limit_for_endpoint("chat") == 25
        assert settings_custom.get_rate_limit_for_endpoint("search") == 100


class TestErrorHandling:
    """Test error handling and validation edge cases."""

    def test_invalid_cors_origins_type(self):
        """Test handling of invalid CORS origins type."""
        with pytest.raises(ValidationError):
            Settings(cors_origins="not-a-list")

    def test_invalid_rate_limit_type(self):
        """Test handling of invalid rate limit types."""
        with pytest.raises(ValidationError):
            Settings(rate_limit_requests="not-a-number")

    def test_negative_rate_limits(self):
        """Test handling of negative rate limits."""
        # Pydantic allows negative integers by default, would need
        # custom validator to restrict
        settings = Settings(rate_limit_requests=-1)
        assert settings.rate_limit_requests == -1

    def test_invalid_boolean_values(self):
        """Test handling of invalid boolean values."""
        with pytest.raises(ValidationError):
            Settings(enable_byok="not-a-boolean")

    def test_empty_string_validation(self):
        """Test handling of empty string values."""
        # Pydantic allows empty strings by default, would need custom validator to
        # restrict
        settings = Settings(api_prefix="")
        assert settings.api_prefix == ""

    def test_none_values_handling(self):
        """Test how None values are handled for optional fields."""
        # This should work for optional fields or fields with defaults
        settings = Settings()
        assert settings.api_prefix is not None  # Has default
        assert settings.cors_origins is not None  # Has default
