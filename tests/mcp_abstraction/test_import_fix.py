"""Test that the circular import fix works."""

import os

# Set minimal required environment variables
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("NEO4J_PASSWORD", "test")

# Mock the settings to avoid cache initialization issues
from unittest.mock import MagicMock

# Create a mock Redis client to avoid connection errors
mock_redis = MagicMock()
mock_redis_module = MagicMock()
mock_redis_module.from_url = MagicMock(return_value=mock_redis)


def test_import_exceptions():
    """Test importing exceptions doesn't trigger circular imports."""
    # This should work without loading all the wrappers
    from tripsage.mcp_abstraction import exceptions

    # Should be able to create exceptions
    error = exceptions.TripSageMCPError("Test error")
    assert str(error) == "Test error"

    print("✓ Successfully imported exceptions without circular imports")


def test_import_base_wrapper():
    """Test importing base wrapper doesn't trigger circular imports."""
    from tripsage.mcp_abstraction import BaseMCPWrapper

    # Should be able to use the base class
    assert BaseMCPWrapper.__name__ == "BaseMCPWrapper"

    print("✓ Successfully imported BaseMCPWrapper without circular imports")


def test_import_registry():
    """Test importing registry doesn't trigger circular imports."""
    from tripsage.mcp_abstraction import registry

    # Registry should exist but not have wrappers loaded yet
    assert registry is not None

    print("✓ Successfully imported registry without circular imports")


def test_lazy_loading():
    """Test that wrappers are loaded lazily."""
    from tripsage.mcp_abstraction.registration import register_default_wrappers
    from tripsage.mcp_abstraction.registry import registry

    # Register wrappers lazily without importing them
    register_default_wrappers()

    # Check that wrappers are not actually loaded yet
    assert len(registry._registry) == 0
    assert len(registry._lazy_loaders) > 0

    # Verify the wrappers were registered lazily
    assert "weather" in registry._lazy_loaders
    assert "google_maps" in registry._lazy_loaders
    assert "time" in registry._lazy_loaders

    print("✓ Successfully registered wrappers for lazy loading")


if __name__ == "__main__":
    test_import_exceptions()
    test_import_base_wrapper()
    test_import_registry()
    test_lazy_loading()
    print("\nAll import tests passed!")
