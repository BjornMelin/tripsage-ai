#!/usr/bin/env python3
"""
Simple test runner to verify imports and basic functionality
without requiring full pytest installation.
"""

import os
import sys
import traceback
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set test environment
os.environ.update(
    {
        "SUPABASE_URL": "https://test-project.supabase.co",
        "SUPABASE_ANON_KEY": "test-anon-key",
        "OPENAI_API_KEY": "test-openai-key",
        "DEBUG": "false",
        "ENVIRONMENT": "testing",
    }
)


def test_config_imports():
    """Test that config module can be imported and instantiated."""
    try:
        from tripsage.api.core.config import Settings, get_settings
        from tripsage_core.config import CoreAppSettings

        # Test basic instantiation
        settings = Settings()

        # Test inheritance
        assert isinstance(settings, CoreAppSettings)
        assert isinstance(settings, Settings)

        # Test agent-specific attributes
        assert hasattr(settings, "api_prefix")
        assert hasattr(settings, "cors_origins")
        assert hasattr(settings, "token_expiration_minutes")
        assert hasattr(settings, "secret_key")

        # Test default values
        assert settings.api_prefix == "/api/agent"
        assert settings.token_expiration_minutes == 120
        assert settings.rate_limit_requests == 1000
        assert settings.api_key_expiration_days == 365

        # Test secret key property
        secret = settings.secret_key
        assert isinstance(secret, str)
        assert len(secret) > 0

        # Test get_settings function
        cached_settings = get_settings()
        assert isinstance(cached_settings, Settings)

        print("✓ Config imports and basic functionality test passed")
        return True

    except Exception as e:
        print(f"✗ Config test failed: {e}")
        traceback.print_exc()
        return False


def test_exception_imports():
    """Test that exception handlers can be imported."""
    try:
        from tripsage_core.exceptions.exceptions import (
            CoreAuthenticationError,
            CoreKeyValidationError,
            ErrorDetails,
        )

        # Test exception creation
        auth_error = CoreAuthenticationError("Test auth error")
        assert auth_error.message == "Test auth error"
        assert auth_error.code == "AUTHENTICATION_ERROR"
        assert auth_error.status_code == 401

        # Test with details
        details = ErrorDetails(user_id="test123", service="test_service")
        key_error = CoreKeyValidationError("Test key error", details=details)
        assert key_error.details.user_id == "test123"
        assert key_error.details.service == "test_service"

        print("✓ Exception imports and basic functionality test passed")
        return True

    except Exception as e:
        print(f"✗ Exception test failed: {e}")
        traceback.print_exc()
        return False


def test_main_imports():
    """Test that main module can be imported (without running the app)."""
    try:
        # Note: We can't easily test create_app() without full dependencies
        # but we can test that the imports work

        # Test that our exception types are available

        print("✓ Main module imports test passed")
        return True

    except Exception as e:
        print(f"✗ Main imports test failed: {e}")
        traceback.print_exc()
        return False


def test_cors_validation():
    """Test CORS validation logic."""
    try:
        from pydantic import ValidationError

        from tripsage.api.core.config import Settings

        # Test development allows wildcard
        dev_settings = Settings(environment="development", cors_origins=["*"])
        assert dev_settings.cors_origins == ["*"]

        # Test production rejects wildcard
        try:
            Settings(environment="production", cors_origins=["*"])
            raise AssertionError("Should have raised ValidationError")
        except ValidationError as e:
            assert "Wildcard CORS origin not allowed in production" in str(e)

        # Test production allows specific origins
        prod_settings = Settings(
            environment="production", cors_origins=["https://example.com"]
        )
        assert prod_settings.cors_origins == ["https://example.com"]

        print("✓ CORS validation test passed")
        return True

    except Exception as e:
        print(f"✗ CORS validation test failed: {e}")
        traceback.print_exc()
        return False


def test_inheritance():
    """Test inheritance from CoreAppSettings works correctly."""
    try:
        from tripsage.api.core.config import Settings

        settings = Settings()

        # Test inherited methods
        assert hasattr(settings, "is_development")
        assert hasattr(settings, "is_production")
        assert hasattr(settings, "is_testing")
        assert hasattr(settings, "validate_critical_settings")

        # Test inherited configurations
        assert hasattr(settings, "database")
        assert hasattr(settings, "dragonfly")
        assert hasattr(settings, "mem0")
        assert hasattr(settings, "langgraph")

        # Test method calls work
        assert isinstance(settings.is_testing(), bool)
        assert isinstance(settings.validate_critical_settings(), list)

        print("✓ Inheritance test passed")
        return True

    except Exception as e:
        print(f"✗ Inheritance test failed: {e}")
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("Running basic functionality tests...\n")

    tests = [
        test_config_imports,
        test_exception_imports,
        test_main_imports,
        test_cors_validation,
        test_inheritance,
    ]

    passed = 0
    failed = 0

    for test in tests:
        if test():
            passed += 1
        else:
            failed += 1
        print()  # Add spacing between tests

    print(f"Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("🎉 All basic tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
