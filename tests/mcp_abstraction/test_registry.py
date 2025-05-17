"""
Tests for the MCPClientRegistry singleton class.

Tests cover:
- Singleton pattern enforcement
- Registration methods (direct and lazy)
- Lookup behavior
- Auto-registration behavior
- Error handling
"""

import importlib
import threading
import unittest.mock
from typing import Any, Dict, List

import pytest

from tripsage.mcp_abstraction.base_wrapper import BaseMCPWrapper
from tripsage.mcp_abstraction.registry import MCPClientRegistry, registry


# Mock MCP wrapper classes
class MockBaseMCPWrapper(BaseMCPWrapper):
    """Mock implementation of BaseMCPWrapper for testing."""

    def __init__(self, client: Any, mcp_name: str):
        super().__init__(client, mcp_name)

    def _build_method_map(self) -> Dict[str, str]:
        return {"test_method": "actual_test_method"}

    def get_available_methods(self) -> List[str]:
        return ["test_method"]


class MockWeatherMCPWrapper(MockBaseMCPWrapper):
    """Mock Weather MCP wrapper for testing."""

    pass


class MockMapsMCPWrapper(MockBaseMCPWrapper):
    """Mock Maps MCP wrapper for testing."""

    pass


class InvalidMCPWrapper:
    """Invalid wrapper that doesn't inherit from BaseMCPWrapper."""

    pass


def test_singleton_pattern():
    """Test that MCPClientRegistry enforces the singleton pattern."""
    # Get two instances
    registry1 = MCPClientRegistry()
    registry2 = MCPClientRegistry()

    # They should be the same object
    assert registry1 is registry2

    # The global registry should also be the same object
    assert registry is registry1
    assert registry is registry2


def test_direct_registration():
    """Test registering a wrapper class directly."""
    # Create a new registry for testing (will be the same singleton)
    test_registry = MCPClientRegistry()

    # Clear any existing registrations for the test MCP name
    # This is a bit of a hack since we can't easily reset the singleton
    test_registry._registry.pop("test_mcp", None)
    test_registry._lazy_loaders.pop("test_mcp", None)

    # Register a wrapper class
    test_registry.register("test_mcp", MockWeatherMCPWrapper)

    # Check it was registered
    assert test_registry.is_registered("test_mcp")
    assert "test_mcp" in test_registry.get_registered_mcps()

    # Get the registered class
    wrapper_class = test_registry.get_wrapper_class("test_mcp")
    assert wrapper_class is MockWeatherMCPWrapper


def test_lazy_registration():
    """Test registering a wrapper class lazily."""
    # Create a new registry for testing
    test_registry = MCPClientRegistry()

    # Clear any existing registrations for the test MCP name
    test_registry._registry.pop("lazy_mcp", None)
    test_registry._lazy_loaders.pop("lazy_mcp", None)

    # Register a lazy loader
    loader_called = False

    def lazy_loader():
        nonlocal loader_called
        loader_called = True
        return MockMapsMCPWrapper

    test_registry.register_lazy("lazy_mcp", lazy_loader)

    # Check it was registered but not loaded yet
    assert test_registry.is_registered("lazy_mcp")
    assert "lazy_mcp" in test_registry.get_registered_mcps()
    assert "lazy_mcp" not in test_registry._registry
    assert "lazy_mcp" in test_registry._lazy_loaders
    assert not loader_called

    # Get the registered class, which should trigger the loader
    wrapper_class = test_registry.get_wrapper_class("lazy_mcp")
    assert loader_called
    assert wrapper_class is MockMapsMCPWrapper

    # Check it's now in the registry
    assert "lazy_mcp" in test_registry._registry


def test_replace_option():
    """Test that replace=False prevents overwriting and replace=True allows it."""
    # Create a new registry for testing
    test_registry = MCPClientRegistry()

    # Set up test MCP names
    direct_mcp = "direct_replace_test"
    lazy_mcp = "lazy_replace_test"

    # Clear any existing registrations
    test_registry._registry.pop(direct_mcp, None)
    test_registry._lazy_loaders.pop(direct_mcp, None)
    test_registry._registry.pop(lazy_mcp, None)
    test_registry._lazy_loaders.pop(lazy_mcp, None)

    # Register initial classes
    test_registry.register(direct_mcp, MockWeatherMCPWrapper)
    test_registry.register_lazy(lazy_mcp, lambda: MockWeatherMCPWrapper)

    # Try to register with replace=False (default)
    with pytest.raises(ValueError):
        test_registry.register(direct_mcp, MockMapsMCPWrapper)

    with pytest.raises(ValueError):
        test_registry.register_lazy(lazy_mcp, lambda: MockMapsMCPWrapper)

    # Register with replace=True
    test_registry.register(direct_mcp, MockMapsMCPWrapper, replace=True)
    test_registry.register_lazy(lazy_mcp, lambda: MockMapsMCPWrapper, replace=True)

    # Check they were replaced
    assert test_registry.get_wrapper_class(direct_mcp) is MockMapsMCPWrapper

    # For lazy loading, we need to check the loader function was replaced
    # This requires implementation knowledge, but it's important to test
    test_registry._lazy_loaders.pop(lazy_mcp)  # Reset to test replacement
    test_registry.register_lazy(lazy_mcp, lambda: MockBaseMCPWrapper, replace=True)
    assert test_registry.get_wrapper_class(lazy_mcp) is MockBaseMCPWrapper


def test_invalid_wrapper_class():
    """Test that non-BaseMCPWrapper classes are rejected."""
    test_registry = MCPClientRegistry()

    with pytest.raises(TypeError):
        test_registry.register("invalid_mcp", InvalidMCPWrapper)


def test_get_nonexistent_wrapper():
    """Test getting a wrapper that doesn't exist."""
    test_registry = MCPClientRegistry()

    # Force auto-register to be called already so we test the error case
    test_registry._auto_register_called = True

    with pytest.raises(KeyError):
        test_registry.get_wrapper_class("nonexistent_mcp")


def test_auto_registration():
    """Test that auto-registration is triggered when needed."""
    # Create a new registry instance
    test_registry = MCPClientRegistry()

    # Reset auto-register flag
    test_registry._auto_register_called = False

    # We need to mock the import of the registration module
    # Let's create a mock registration module
    mock_registration = unittest.mock.MagicMock()
    mock_registration.register_default_wrappers = unittest.mock.MagicMock()

    # Mock sys.modules to simulate the registration module
    mock_modules = {"tripsage.mcp_abstraction.registration": mock_registration}
    with unittest.mock.patch.dict("sys.modules", mock_modules):
        # Try to get a wrapper that doesn't exist, triggering auto-registration
        with pytest.raises(KeyError):
            test_registry.get_wrapper_class("trigger_auto_register")

        # Verify auto-registration was called
        mock_registration.register_default_wrappers.assert_called_once()
        assert test_registry._auto_register_called is True


def test_auto_registration_error_handling():
    """Test that auto-registration handles import errors gracefully."""
    test_registry = MCPClientRegistry()

    # Reset auto-register flag
    test_registry._auto_register_called = False

    # Mock import error
    mock_modules = {"tripsage.mcp_abstraction.registration": None}
    with unittest.mock.patch.dict("sys.modules", mock_modules):
        # This should trigger auto-registration which will fail with ImportError
        with pytest.raises(KeyError):
            importlib.reload(pytest.importorskip("tripsage.mcp_abstraction.registry"))
            test_registry.get_wrapper_class("trigger_auto_register_error")

        # Even with error, the flag should be set to prevent repeated attempts
        assert test_registry._auto_register_called is True


def test_threadsafe_singleton():
    """Test that the singleton pattern is thread-safe."""
    # Shared list to store registry instances created in threads
    registries = []

    def create_registry():
        registry = MCPClientRegistry()
        registries.append(registry)

    # Create multiple threads to create registry instances
    threads = [threading.Thread(target=create_registry) for _ in range(10)]

    # Start all threads
    for thread in threads:
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    # Check that all created registries are the same instance
    first_registry = registries[0]
    for reg in registries[1:]:
        assert reg is first_registry


def test_get_registered_mcps():
    """Test getting the list of registered MCPs."""
    test_registry = MCPClientRegistry()

    # Clear existing registrations for test MCPs
    for mcp in ["list_test1", "list_test2", "list_test3"]:
        test_registry._registry.pop(mcp, None)
        test_registry._lazy_loaders.pop(mcp, None)

    # Register some test MCPs
    test_registry.register("list_test1", MockWeatherMCPWrapper)
    test_registry.register_lazy("list_test2", lambda: MockMapsMCPWrapper)
    test_registry.register("list_test3", MockBaseMCPWrapper)

    # Get the list
    registered_mcps = test_registry.get_registered_mcps()

    # Check all our test MCPs are in the list
    assert "list_test1" in registered_mcps
    assert "list_test2" in registered_mcps
    assert "list_test3" in registered_mcps
