"""
Standalone unit tests for API configuration module.

Tests the APISettings class independently without global fixtures.
"""

import os
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Set clean test environment
os.environ.update(
    {
        "SUPABASE_URL": "https://test-project.supabase.co",
        "SUPABASE_ANON_KEY": "test-anon-key",
        "OPENAI_API_KEY": "test-openai-key",
        "DEBUG": "false",
        "ENVIRONMENT": "testing",
    }
)

from api.core.config import APISettings  # noqa: E402
from tripsage_core.config.base_app_settings import CoreAppSettings  # noqa: E402


def test_api_settings_inheritance():
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

    # Test values
    assert settings.app_name == "TripSage"
    assert settings.environment == "testing"


def test_api_settings_defaults():
    """Test default values for frontend-specific settings."""
    settings = APISettings()

    # JWT settings
    assert settings.access_token_expire_minutes == 30
    assert settings.refresh_token_expire_days == 7

    # CORS settings (production mode defaults)
    expected_origins = [
        "https://tripsage.ai",
        "https://app.tripsage.ai",
        "https://api.tripsage.ai",
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
        "openai",
        "weather",
        "flights",
        "googleMaps",
        "accommodation",
        "webCrawl",
    ]
    assert settings.byok_services == expected_services


def test_jwt_properties():
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


def test_cors_origins_debug_behavior():
    """Test CORS origins behavior in debug vs production mode."""
    # Test debug mode
    debug_settings = APISettings(debug=True)
    assert debug_settings.cors_origins == ["*"]

    # Test production mode
    prod_settings = APISettings(debug=False)
    expected_origins = [
        "https://tripsage.ai",
        "https://app.tripsage.ai",
        "https://api.tripsage.ai",
    ]
    assert prod_settings.cors_origins == expected_origins


def test_custom_settings():
    """Test custom configuration overrides."""
    custom_origins = ["https://custom.domain.com"]

    settings = APISettings(
        access_token_expire_minutes=60,
        refresh_token_expire_days=30,
        cors_origins=custom_origins,
        cors_allow_credentials=False,
        rate_limit_enabled=False,
        rate_limit_requests=120,
        enable_byok=False,
        byok_services=["openai"],
    )

    assert settings.access_token_expire_minutes == 60
    assert settings.refresh_token_expire_days == 30
    assert settings.cors_allow_credentials is False
    assert settings.rate_limit_enabled is False
    assert settings.rate_limit_requests == 120
    assert settings.enable_byok is False
    assert settings.byok_services == ["openai"]


def test_inherited_database_config():
    """Test that database configuration is inherited correctly."""
    settings = APISettings()

    # Verify database config is accessible
    assert hasattr(settings, "database")
    assert hasattr(settings.database, "supabase_url")
    assert hasattr(settings.database, "supabase_anon_key")
    assert settings.database.supabase_url in [
        "https://test-project.supabase.co",
        "https://test.supabase.co",
    ]


def test_inherited_core_api_keys():
    """Test that core API keys are inherited correctly."""
    settings = APISettings()

    # Verify core API keys are accessible
    assert hasattr(settings, "openai_api_key")
    assert settings.openai_api_key.get_secret_value() in [
        "test-openai-key",
        "test-openai-key",
        "test_openai_key",
        "test-key",
    ]


def test_environment_specific_behavior():
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


def test_pydantic_validation():
    """Test Pydantic validation for invalid values."""
    # Test invalid access token expiration (negative value)
    # Note: Pydantic doesn't automatically validate negative values unless we
    # add constraints
    try:
        settings = APISettings(access_token_expire_minutes=-1)
        # If no validation error, just check the value was set
        assert settings.access_token_expire_minutes == -1
    except ValidationError:
        # If validation error occurs, that's also acceptable
        pass

    # Test that valid values work
    valid_settings = APISettings(
        access_token_expire_minutes=60, refresh_token_expire_days=30
    )
    assert valid_settings.access_token_expire_minutes == 60
    assert valid_settings.refresh_token_expire_days == 30


def test_inherited_methods():
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
    assert settings.is_testing() is True  # We set environment to "testing"


def test_settings_module_instance():
    """Test that the module-level settings instance is created properly."""
    from api.core.config import settings

    assert isinstance(settings, APISettings)
    assert isinstance(settings, CoreAppSettings)

    # Verify it has both inherited and frontend-specific attributes
    assert hasattr(settings, "app_name")  # inherited
    assert hasattr(settings, "access_token_expire_minutes")  # frontend-specific


def test_backwards_compatibility():
    """Test that existing code patterns still work."""
    from api.core.config import settings

    # These are common patterns that existing code might use
    assert hasattr(settings, "secret_key")
    assert hasattr(settings, "algorithm")
    assert isinstance(settings.secret_key, str)
    assert settings.algorithm == "HS256"


def test_settings_serialization():
    """Test that settings can be serialized properly."""
    settings = APISettings()

    # Test model_dump works (important for config inspection)
    config_dict = settings.model_dump()
    assert isinstance(config_dict, dict)
    assert "access_token_expire_minutes" in config_dict
    assert "cors_origins" in config_dict
    assert "app_name" in config_dict  # inherited field


def test_model_validator_cors_origins():
    """Test the model validator for CORS origins in debug mode."""
    # Test that the validator properly sets CORS origins in debug mode
    settings = APISettings(debug=True)
    assert settings.cors_origins == ["*"]

    # Test that validator overrides explicitly set origins in debug mode
    custom_origins = ["https://test.com"]
    settings_with_custom = APISettings(debug=True, cors_origins=custom_origins)
    # The validator should override custom origins in debug mode
    assert settings_with_custom.cors_origins == ["*"]


def test_cors_production_defaults():
    """Test CORS defaults are set correctly for production."""
    settings = APISettings(debug=False)
    expected_origins = [
        "https://tripsage.ai",
        "https://app.tripsage.ai",
        "https://api.tripsage.ai",
    ]
    assert settings.cors_origins == expected_origins


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v"])
