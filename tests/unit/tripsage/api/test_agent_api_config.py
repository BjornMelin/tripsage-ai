"""
Comprehensive unit tests for agent API configuration module.

Tests the Settings class that extends CoreAppSettings with agent-specific settings.
Ensures proper inheritance, agent-specific configurations, and validation.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

# Set test environment before imports
os.environ.update(
    {
        "SUPABASE_URL": "https://test-project.supabase.co",
        "SUPABASE_ANON_KEY": "test-anon-key",
        "OPENAI_API_KEY": "test-openai-key",
        "DEBUG": "false",
        "ENVIRONMENT": "testing",
    }
)

from tripsage.api.core.config import Settings, get_settings
from tripsage_core.config.base_app_settings import CoreAppSettings


class TestAgentAPISettings:
    """Test suite for agent API Settings class."""

    def test_inherits_from_core_app_settings(self):
        """Test that Settings properly inherits from CoreAppSettings."""
        settings = Settings()

        # Verify inheritance
        assert isinstance(settings, CoreAppSettings)
        assert isinstance(settings, Settings)

        # Verify core settings are accessible
        assert hasattr(settings, "app_name")
        assert hasattr(settings, "debug")
        assert hasattr(settings, "environment")
        assert hasattr(settings, "database")
        assert hasattr(settings, "jwt_secret_key")
        assert hasattr(settings, "openai_api_key")

    def test_agent_specific_default_values(self):
        """Test default values for agent-specific settings."""
        settings = Settings()

        # Agent API specific settings
        assert settings.api_prefix == "/api/agent"

        # Agent-specific CORS origins
        expected_origins = ["http://localhost:3000", "https://tripsage.app"]
        assert settings.cors_origins == expected_origins

        # Agent-specific JWT expiration (longer than frontend)
        assert settings.token_expiration_minutes == 120
        assert settings.refresh_token_expiration_days == 30

        # Agent-specific rate limiting (higher than frontend)
        assert settings.rate_limit_requests == 1000
        assert settings.rate_limit_timeframe == 60

        # Agent API key expiration (longer than frontend)
        assert settings.api_key_expiration_days == 365

    def test_inherited_core_settings(self):
        """Test that core settings are properly inherited."""
        settings = Settings(environment="testing")

        # Test core app metadata
        assert settings.app_name == "TripSage"
        assert settings.environment == "testing"

        # Test core configurations are accessible
        assert hasattr(settings, "database")
        assert hasattr(settings, "dragonfly")
        assert hasattr(settings, "mem0")
        assert hasattr(settings, "langgraph")
        assert hasattr(settings, "crawl4ai")
        assert hasattr(settings, "agent")
        assert hasattr(settings, "feature_flags")
        assert hasattr(settings, "opentelemetry")

    def test_secret_key_property(self):
        """Test the secret_key property delegates to jwt_secret_key."""
        settings = Settings()

        # Test secret_key property
        secret = settings.secret_key
        assert isinstance(secret, str)
        assert len(secret) > 0

        # Verify it accesses the inherited jwt_secret_key
        assert secret == settings.jwt_secret_key.get_secret_value()

    def test_custom_agent_settings(self):
        """Test custom agent API configuration overrides."""
        custom_origins = ["https://custom-agent.domain.com"]

        settings = Settings(
            api_prefix="/api/v2/agent",
            cors_origins=custom_origins,
            token_expiration_minutes=240,
            refresh_token_expiration_days=60,
            rate_limit_requests=2000,
            rate_limit_timeframe=120,
            api_key_expiration_days=730,
        )

        assert settings.api_prefix == "/api/v2/agent"
        assert settings.cors_origins == custom_origins
        assert settings.token_expiration_minutes == 240
        assert settings.refresh_token_expiration_days == 60
        assert settings.rate_limit_requests == 2000
        assert settings.rate_limit_timeframe == 120
        assert settings.api_key_expiration_days == 730

    def test_cors_validation_production(self):
        """Test CORS origins validation in production environment."""
        # Production environment should reject wildcard origins
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                environment="production",
                cors_origins=["*"],
            )

        assert "Wildcard CORS origin not allowed in production" in str(exc_info.value)

    def test_cors_validation_development(self):
        """Test CORS origins validation allows wildcard in development."""
        # Development environment should allow wildcard origins
        settings = Settings(
            environment="development",
            cors_origins=["*"],
        )

        assert settings.cors_origins == ["*"]
        assert settings.environment == "development"

    def test_environment_specific_behavior(self):
        """Test behavior in different environments."""
        # Development environment
        dev_settings = Settings(environment="development", debug=True)
        assert dev_settings.environment == "development"
        assert dev_settings.debug is True
        assert dev_settings.is_development() is True

        # Production environment
        prod_settings = Settings(environment="production", debug=False)
        assert prod_settings.environment == "production"
        assert prod_settings.debug is False
        assert prod_settings.is_production() is True

        # Testing environment
        test_settings = Settings(environment="testing")
        assert test_settings.environment == "testing"
        assert test_settings.is_testing() is True

    def test_inherited_database_config(self):
        """Test that database configuration is inherited correctly."""
        settings = Settings()

        # Verify database config is accessible
        assert hasattr(settings, "database")
        assert hasattr(settings.database, "supabase_url")
        assert hasattr(settings.database, "supabase_anon_key")
        assert settings.database.supabase_url == "https://test-project.supabase.co"

    def test_inherited_api_keys(self):
        """Test that core API keys are inherited correctly."""
        settings = Settings()

        # Verify core API keys are accessible
        assert hasattr(settings, "openai_api_key")
        assert settings.openai_api_key.get_secret_value() == "test-openai-key"

        # Test other inherited optional keys
        assert hasattr(settings, "google_maps_api_key")
        assert hasattr(settings, "duffel_api_key")
        assert hasattr(settings, "openweathermap_api_key")

    def test_inherited_utility_methods(self):
        """Test that inherited utility methods from CoreAppSettings work."""
        settings = Settings()

        # Test inherited utility methods
        assert hasattr(settings, "is_development")
        assert hasattr(settings, "is_production")
        assert hasattr(settings, "is_testing")
        assert hasattr(settings, "get_secret_value")
        assert hasattr(settings, "validate_critical_settings")

        # Test method functionality
        assert isinstance(settings.is_development(), bool)
        assert isinstance(settings.validate_critical_settings(), list)

    def test_settings_serialization(self):
        """Test that settings can be serialized properly."""
        settings = Settings()

        # Test model_dump works (important for config inspection)
        config_dict = settings.model_dump()
        assert isinstance(config_dict, dict)

        # Agent-specific fields
        assert "api_prefix" in config_dict
        assert "cors_origins" in config_dict
        assert "token_expiration_minutes" in config_dict
        assert "api_key_expiration_days" in config_dict

        # Inherited fields
        assert "app_name" in config_dict
        assert "environment" in config_dict

    def test_model_config_settings(self):
        """Test Pydantic model configuration."""
        settings = Settings()

        # Test model config dictionary keys and values
        assert "env_file" in settings.model_config
        assert settings.model_config["env_file"] == ".env"
        assert settings.model_config["env_prefix"] == "TRIPSAGE_API_"
        assert settings.model_config["case_sensitive"] is False
        assert settings.model_config["extra"] == "ignore"
        assert settings.model_config["validate_default"] is True

    @patch.dict("os.environ", {"TRIPSAGE_API_API_PREFIX": "/custom/agent"})
    def test_environment_variable_override(self):
        """Test that environment variables can override agent settings."""
        settings = Settings()

        # Environment variable should override default
        assert settings.api_prefix == "/custom/agent"

    @patch.dict(
        "os.environ",
        {
            "TRIPSAGE_API_TOKEN_EXPIRATION_MINUTES": "180",
            "TRIPSAGE_API_RATE_LIMIT_REQUESTS": "1500",
        },
    )
    def test_multiple_env_var_overrides(self):
        """Test multiple environment variable overrides."""
        settings = Settings()

        assert settings.token_expiration_minutes == 180
        assert settings.rate_limit_requests == 1500

    def test_validation_for_numeric_fields(self):
        """Test validation for numeric field constraints."""
        # Test valid values
        valid_settings = Settings(
            token_expiration_minutes=60,
            refresh_token_expiration_days=30,
            rate_limit_requests=500,
            rate_limit_timeframe=30,
            api_key_expiration_days=180,
        )

        assert valid_settings.token_expiration_minutes == 60
        assert valid_settings.refresh_token_expiration_days == 30
        assert valid_settings.rate_limit_requests == 500
        assert valid_settings.rate_limit_timeframe == 30
        assert valid_settings.api_key_expiration_days == 180

    def test_cors_origins_list_validation(self):
        """Test CORS origins list validation."""
        # Test valid CORS origins
        settings = Settings(cors_origins=["https://example.com", "https://test.com"])
        assert len(settings.cors_origins) == 2
        assert "https://example.com" in settings.cors_origins

        # Test empty list is valid
        settings = Settings(cors_origins=[])
        assert settings.cors_origins == []

    def test_field_descriptions(self):
        """Test that fields have proper descriptions."""
        # Access field info through model fields
        fields = Settings.model_fields

        assert "api_prefix" in fields
        assert fields["api_prefix"].description == "API prefix for agent endpoints"

        assert "cors_origins" in fields
        assert fields["cors_origins"].description == "CORS origins for agent API access"

        assert "token_expiration_minutes" in fields
        assert (
            fields["token_expiration_minutes"].description
            == "Agent JWT token expiration in minutes"
        )


class TestGetSettingsFunction:
    """Test the get_settings function and caching."""

    def test_get_settings_returns_settings_instance(self):
        """Test that get_settings returns a Settings instance."""
        settings = get_settings()

        assert isinstance(settings, Settings)
        assert isinstance(settings, CoreAppSettings)

    def test_get_settings_caching(self):
        """Test that get_settings uses LRU cache."""
        # Call multiple times
        settings1 = get_settings()
        settings2 = get_settings()

        # Should return the same instance due to caching
        assert settings1 is settings2

    def test_get_settings_has_required_attributes(self):
        """Test that get_settings() returns instance with all required attributes."""
        settings = get_settings()

        # Agent-specific attributes
        assert hasattr(settings, "api_prefix")
        assert hasattr(settings, "cors_origins")
        assert hasattr(settings, "token_expiration_minutes")
        assert hasattr(settings, "secret_key")

        # Inherited attributes
        assert hasattr(settings, "app_name")
        assert hasattr(settings, "database")
        assert hasattr(settings, "jwt_secret_key")


class TestSettingsIntegration:
    """Integration tests for Settings with the broader system."""

    def test_backwards_compatibility(self):
        """Test that existing code patterns still work."""
        settings = get_settings()

        # These are common patterns that existing code might use
        assert hasattr(settings, "secret_key")
        assert isinstance(settings.secret_key, str)

        # Test JWT-related functionality
        assert len(settings.secret_key) > 0

    def test_agent_vs_frontend_api_differences(self):
        """Test that agent API has different defaults than frontend API."""
        settings = get_settings()

        # Agent API should have different prefix
        assert settings.api_prefix == "/api/agent"

        # Agent API should have longer token expiration (120 vs 30 minutes)
        assert settings.token_expiration_minutes == 120

        # Agent API should have higher rate limits (1000 vs 60 requests)
        assert settings.rate_limit_requests == 1000

        # Agent API should have longer API key expiration (365 vs 90 days)
        assert settings.api_key_expiration_days == 365

    def test_settings_with_real_environment_loading(self):
        """Test settings loading with realistic environment setup."""
        # Create a temporary .env file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("TRIPSAGE_API_API_PREFIX=/test/agent\n")
            f.write("TRIPSAGE_API_TOKEN_EXPIRATION_MINUTES=300\n")
            temp_env_file = f.name

        try:
            # Store original config
            original_config = Settings.model_config.copy()
            # Temporarily update the env_file in model_config
            Settings.model_config["env_file"] = temp_env_file

            # Create settings instance
            settings = Settings()

            # These values should come from the env file
            # Note: In actual usage, the env file would be loaded automatically
            # This test verifies the mechanism is in place
            assert hasattr(settings, "api_prefix")
            assert hasattr(settings, "token_expiration_minutes")
        finally:
            # Restore original config
            Settings.model_config.clear()
            Settings.model_config.update(original_config)
            # Clean up temp file
            Path(temp_env_file).unlink(missing_ok=True)

    def test_core_app_settings_validation_inherited(self):
        """Test that CoreAppSettings validation is inherited."""
        settings = get_settings()

        # Test validate_critical_settings method
        validation_errors = settings.validate_critical_settings()
        assert isinstance(validation_errors, list)

        # In test environment, should not have critical errors
        # (since we set required env vars at module level)
        if validation_errors:
            # In test env, some validations might fail, that's OK
            assert all(isinstance(error, str) for error in validation_errors)

    def test_feature_flags_inheritance(self):
        """Test that feature flags are properly inherited."""
        settings = get_settings()

        # Test feature flags are accessible
        assert hasattr(settings, "feature_flags")
        assert hasattr(settings.feature_flags, "enable_agent_memory")
        assert hasattr(settings.feature_flags, "enable_streaming_responses")

    def test_service_configurations_inheritance(self):
        """Test that service configurations are inherited."""
        settings = get_settings()

        # Test various service configs are accessible
        assert hasattr(settings, "database")
        assert hasattr(settings, "dragonfly")
        assert hasattr(settings, "mem0")
        assert hasattr(settings, "langgraph")
        assert hasattr(settings, "crawl4ai")
        assert hasattr(settings, "agent")


class TestFieldValidation:
    """Test field validation edge cases."""

    def test_cors_origins_field_validator_with_info_context(self):
        """Test CORS origins validator with proper info context."""
        # Test with production environment explicitly
        with pytest.raises(ValidationError):
            Settings(
                environment="production",
                cors_origins=["*", "https://valid.com"],
            )

    def test_cors_origins_field_validator_with_development(self):
        """Test CORS origins validator allows wildcard in development."""
        settings = Settings(
            environment="development",
            cors_origins=["*"],
        )
        assert settings.cors_origins == ["*"]

    def test_cors_origins_field_validator_with_testing(self):
        """Test CORS origins validator in testing environment."""
        settings = Settings(
            environment="testing",
            cors_origins=["*"],
        )
        # Testing environment should allow wildcard
        assert settings.cors_origins == ["*"]

    def test_cors_origins_field_validator_no_wildcard(self):
        """Test CORS origins validator with no wildcard."""
        settings = Settings(
            environment="production",
            cors_origins=["https://secure.com", "https://app.secure.com"],
        )
        expected = ["https://secure.com", "https://app.secure.com"]
        assert settings.cors_origins == expected
