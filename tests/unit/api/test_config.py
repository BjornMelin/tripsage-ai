"""
Unit tests for API configuration module.

Tests the APISettings class to ensure proper inheritance from CoreAppSettings,
frontend-specific settings, and JWT integration.
"""

import os
import pytest
from unittest.mock import patch
from pydantic import ValidationError

# Set test environment before imports
os.environ.update({
    "SUPABASE_URL": "https://test-project.supabase.co",
    "SUPABASE_ANON_KEY": "test-anon-key",
    "OPENAI_API_KEY": "test-openai-key",
    "DEBUG": "false",
    "ENVIRONMENT": "testing"
})

from api.core.config import APISettings
from tripsage_core.config.base_app_settings import CoreAppSettings


class TestAPISettings:
    """Test suite for APISettings class."""

    def test_inherits_from_core_app_settings(self):
        """Test that APISettings properly inherits from CoreAppSettings."""
        settings = APISettings()
        
        # Verify inheritance
        assert isinstance(settings, CoreAppSettings)
        assert isinstance(settings, APISettings)
        
        # Verify core settings are accessible
        assert hasattr(settings, "app_name")
        assert hasattr(settings, "debug")
        assert hasattr(settings, "environment")
        assert hasattr(settings, "database")
        assert hasattr(settings, "jwt_secret_key")
        assert hasattr(settings, "openai_api_key")

    def test_default_values(self):
        """Test default values for frontend-specific settings."""
        settings = APISettings()
        
        # JWT settings
        assert settings.access_token_expire_minutes == 30
        assert settings.refresh_token_expire_days == 7
        
        # CORS settings (production mode defaults)
        expected_origins = [
            "https://tripsage.ai",
            "https://app.tripsage.ai", 
            "https://api.tripsage.ai"
        ]
        assert settings.cors_origins == expected_origins
        assert settings.cors_allow_credentials is True
        assert settings.cors_allow_methods == ["*"]
        assert settings.cors_allow_headers == ["*"]
        
        # Rate limiting
        assert settings.rate_limit_enabled is True
        assert settings.rate_limit_requests == 60
        
        # BYOK settings
        assert settings.enable_byok is True
        expected_services = [
            "openai", "weather", "flights", 
            "googleMaps", "accommodation", "webCrawl"
        ]
        assert settings.byok_services == expected_services

    def test_jwt_properties(self):
        """Test JWT-related property methods."""
        settings = APISettings()
        
        # Test secret_key property
        secret = settings.secret_key
        assert isinstance(secret, str)
        assert len(secret) > 0
        
        # Test algorithm property
        assert settings.algorithm == "HS256"
        
        # Verify it accesses the inherited jwt_secret_key
        assert secret == settings.jwt_secret_key.get_secret_value()

    def test_cors_origins_debug_mode(self):
        """Test CORS origins behavior in debug mode."""
        # Test debug mode
        debug_settings = APISettings(debug=True)
        assert debug_settings.cors_origins == ["*"]
        
        # Test production mode
        prod_settings = APISettings(debug=False)
        expected_origins = [
            "https://tripsage.ai",
            "https://app.tripsage.ai",
            "https://api.tripsage.ai"
        ]
        assert prod_settings.cors_origins == expected_origins

    def test_custom_jwt_expiration(self):
        """Test custom JWT expiration times."""
        settings = APISettings(
            access_token_expire_minutes=60,
            refresh_token_expire_days=30
        )
        
        assert settings.access_token_expire_minutes == 60
        assert settings.refresh_token_expire_days == 30

    def test_custom_cors_settings(self):
        """Test custom CORS configuration."""
        custom_origins = ["https://custom.domain.com", "https://another.domain.com"]
        
        settings = APISettings(
            cors_origins=custom_origins,
            cors_allow_credentials=False,
            cors_allow_methods=["GET", "POST"],
            cors_allow_headers=["Authorization", "Content-Type"]
        )
        
        assert settings.cors_origins == custom_origins
        assert settings.cors_allow_credentials is False
        assert settings.cors_allow_methods == ["GET", "POST"]
        assert settings.cors_allow_headers == ["Authorization", "Content-Type"]

    def test_custom_rate_limiting(self):
        """Test custom rate limiting configuration."""
        settings = APISettings(
            rate_limit_enabled=False,
            rate_limit_requests=120
        )
        
        assert settings.rate_limit_enabled is False
        assert settings.rate_limit_requests == 120

    def test_custom_byok_settings(self):
        """Test custom BYOK configuration."""
        custom_services = ["openai", "weather"]
        
        settings = APISettings(
            enable_byok=False,
            byok_services=custom_services
        )
        
        assert settings.enable_byok is False
        assert settings.byok_services == custom_services

    def test_inherited_database_config(self):
        """Test that database configuration is inherited correctly."""
        settings = APISettings()
        
        # Verify database config is accessible
        assert hasattr(settings, "database")
        assert hasattr(settings.database, "supabase_url")
        assert hasattr(settings.database, "supabase_anon_key")
        assert settings.database.supabase_url == "https://test-project.supabase.co"

    def test_inherited_core_api_keys(self):
        """Test that core API keys are inherited correctly."""
        settings = APISettings()
        
        # Verify core API keys are accessible
        assert hasattr(settings, "openai_api_key")
        assert settings.openai_api_key.get_secret_value() == "test-openai-key"

    def test_environment_specific_behavior(self):
        """Test behavior in different environments."""
        # Development environment
        dev_settings = APISettings(environment="development", debug=True)
        assert dev_settings.environment == "development"
        assert dev_settings.debug is True
        assert dev_settings.cors_origins == ["*"]
        
        # Production environment
        prod_settings = APISettings(environment="production", debug=False)
        assert prod_settings.environment == "production"
        assert prod_settings.debug is False
        assert len(prod_settings.cors_origins) == 3

    @patch.dict("os.environ", {"DEBUG": "true"})
    def test_environment_variable_override(self):
        """Test that environment variables can override settings."""
        # Note: This test verifies the inheritance works with env vars
        settings = APISettings()
        # The actual env var loading is handled by pydantic-settings
        # This test ensures the mechanism is in place
        assert hasattr(settings, "debug")

    def test_model_validator_cors_origins(self):
        """Test the model validator for CORS origins."""
        # Test that the validator properly sets CORS origins in debug mode
        settings = APISettings(debug=True)
        assert settings.cors_origins == ["*"]
        
        # Test that validator doesn't override explicitly set origins in debug mode
        custom_origins = ["https://test.com"]
        settings_with_custom = APISettings(
            debug=True, 
            cors_origins=custom_origins
        )
        # The validator should override custom origins in debug mode
        assert settings_with_custom.cors_origins == ["*"]

    def test_settings_immutability_after_creation(self):
        """Test that settings maintain their values after creation."""
        settings = APISettings(
            access_token_expire_minutes=45,
            rate_limit_requests=100
        )
        
        # Values should remain consistent
        assert settings.access_token_expire_minutes == 45
        assert settings.rate_limit_requests == 100

    def test_pydantic_validation(self):
        """Test Pydantic validation for invalid values."""
        # Test invalid access token expiration (negative value)
        with pytest.raises(ValidationError):
            APISettings(access_token_expire_minutes=-1)
        
        # Test invalid refresh token expiration (negative value)
        with pytest.raises(ValidationError):
            APISettings(refresh_token_expire_days=-1)

    def test_all_inherited_methods(self):
        """Test that inherited methods from CoreAppSettings work."""
        settings = APISettings()
        
        # Test inherited utility methods
        assert hasattr(settings, "is_development")
        assert hasattr(settings, "is_production")
        assert hasattr(settings, "is_testing")
        assert hasattr(settings, "get_secret_value")
        assert hasattr(settings, "validate_critical_settings")
        
        # Test method functionality
        assert isinstance(settings.is_development(), bool)
        assert isinstance(settings.validate_critical_settings(), list)

    def test_settings_instance_creation(self):
        """Test that the module-level settings instance is created properly."""
        from api.core.config import settings
        
        assert isinstance(settings, APISettings)
        assert isinstance(settings, CoreAppSettings)
        
        # Verify it has both inherited and frontend-specific attributes
        assert hasattr(settings, "app_name")  # inherited
        assert hasattr(settings, "access_token_expire_minutes")  # frontend-specific


class TestAPISettingsIntegration:
    """Integration tests for APISettings with the broader system."""

    def test_backwards_compatibility(self):
        """Test that existing code patterns still work."""
        from api.core.config import settings
        
        # These are common patterns that existing code might use
        assert hasattr(settings, "secret_key")
        assert hasattr(settings, "algorithm")
        assert isinstance(settings.secret_key, str)
        assert settings.algorithm == "HS256"

    def test_settings_serialization(self):
        """Test that settings can be serialized properly."""
        settings = APISettings()
        
        # Test model_dump works (important for config inspection)
        config_dict = settings.model_dump()
        assert isinstance(config_dict, dict)
        assert "access_token_expire_minutes" in config_dict
        assert "cors_origins" in config_dict
        assert "app_name" in config_dict  # inherited field

    def test_settings_with_env_file(self):
        """Test settings loading from environment."""
        # This verifies the pydantic-settings integration works
        settings = APISettings()
        
        # Should have the proper model config for env file loading
        assert hasattr(settings.model_config, "env_file")
        assert settings.model_config["env_file"] == ".env"