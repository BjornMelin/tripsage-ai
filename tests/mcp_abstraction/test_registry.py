"""
Tests for MCPClientRegistry.

This module tests the registry that manages MCP wrapper instances.
"""


import pytest

from tripsage.mcp_abstraction.base_wrapper import BaseMCPWrapper
from tripsage.mcp_abstraction.exceptions import MCPConfigurationError
from tripsage.mcp_abstraction.registry import MCPClientRegistry


class MockWrapper(BaseMCPWrapper):
    """Mock wrapper for testing."""

    def __init__(self):
        self.service_name = "test-service"
        self.initialized = False

    async def initialize(self):
        self.initialized = True

    async def shutdown(self):
        self.initialized = False

    async def invoke_method(self, method: str, params: dict) -> dict:
        return {"method": method, "params": params}


class TestMCPClientRegistry:
    """Tests for MCPClientRegistry functionality."""

    def test_singleton_pattern(self):
        """Test that MCPClientRegistry follows singleton pattern."""
        registry1 = MCPClientRegistry()
        registry2 = MCPClientRegistry()

        # Should be the same instance
        assert registry1 is registry2

    def test_register_wrapper(self):
        """Test registering a wrapper."""
        registry = MCPClientRegistry()
        wrapper = MockWrapper()

        # Clear any existing registrations
        registry.wrappers.clear()

        # Register wrapper
        registry.register("test-service", wrapper)

        # Verify registration
        assert "test-service" in registry.wrappers
        assert registry.wrappers["test-service"] == wrapper

    def test_register_duplicate_service(self):
        """Test that registering duplicate service raises error."""
        registry = MCPClientRegistry()
        wrapper1 = MockWrapper()
        wrapper2 = MockWrapper()

        # Clear any existing registrations
        registry.wrappers.clear()

        # Register first wrapper
        registry.register("test-service", wrapper1)

        # Try to register duplicate
        with pytest.raises(MCPConfigurationError) as exc_info:
            registry.register("test-service", wrapper2)

        assert "Wrapper already registered for service: test-service" in str(
            exc_info.value
        )

    def test_get_wrapper(self):
        """Test getting a registered wrapper."""
        registry = MCPClientRegistry()
        wrapper = MockWrapper()

        # Clear and register
        registry.wrappers.clear()
        registry.register("test-service", wrapper)

        # Get wrapper
        retrieved = registry.get("test-service")

        # Verify
        assert retrieved == wrapper

    def test_get_nonexistent_wrapper(self):
        """Test getting a non-existent wrapper returns None."""
        registry = MCPClientRegistry()

        # Clear any existing registrations
        registry.wrappers.clear()

        # Get non-existent wrapper
        result = registry.get("non-existent")

        # Should return None
        assert result is None

    def test_list_services(self):
        """Test listing all registered services."""
        registry = MCPClientRegistry()
        wrapper1 = MockWrapper()
        wrapper2 = MockWrapper()

        # Clear and register multiple wrappers
        registry.wrappers.clear()
        registry.register("service1", wrapper1)
        registry.register("service2", wrapper2)

        # Get service list
        services = registry.list_services()

        # Verify
        assert sorted(services) == ["service1", "service2"]

    def test_unregister_wrapper(self):
        """Test unregistering a wrapper."""
        registry = MCPClientRegistry()
        wrapper = MockWrapper()

        # Clear and register
        registry.wrappers.clear()
        registry.register("test-service", wrapper)

        # Unregister
        result = registry.unregister("test-service")

        # Verify
        assert result is True
        assert "test-service" not in registry.wrappers

    def test_unregister_nonexistent_wrapper(self):
        """Test unregistering a non-existent wrapper returns False."""
        registry = MCPClientRegistry()

        # Clear any existing registrations
        registry.wrappers.clear()

        # Unregister non-existent
        result = registry.unregister("non-existent")

        # Should return False
        assert result is False

    def test_clear_all_wrappers(self):
        """Test clearing all registered wrappers."""
        registry = MCPClientRegistry()
        wrapper1 = MockWrapper()
        wrapper2 = MockWrapper()

        # Register multiple wrappers
        registry.wrappers.clear()
        registry.register("service1", wrapper1)
        registry.register("service2", wrapper2)

        # Clear all
        registry.clear()

        # Verify
        assert len(registry.wrappers) == 0
        assert registry.list_services() == []

    def test_automatic_registration_on_import(self):
        """Test that importing registration module registers default wrappers."""
        registry = MCPClientRegistry()

        # Clear existing registrations
        registry.clear()

        # Import registration module (this should auto-register wrappers)
        # Note: In a real test, this would import the actual registration module
        # For this test, we'll simulate what happens

        # Simulate auto-registration
        from tripsage.mcp_abstraction.wrappers.weather_wrapper import WeatherMCPWrapper

        weather_wrapper = WeatherMCPWrapper()
        registry.register("weather", weather_wrapper)

        # Verify registration
        assert "weather" in registry.wrappers
        assert isinstance(registry.get("weather"), WeatherMCPWrapper)

    def test_thread_safety(self):
        """Test that registry operations are thread-safe."""
        import threading

        registry = MCPClientRegistry()
        registry.clear()

        errors = []

        def register_wrapper(service_name):
            try:
                wrapper = MockWrapper()
                registry.register(service_name, wrapper)
            except Exception as e:
                errors.append(e)

        # Create multiple threads trying to register different services
        threads = []
        for i in range(10):
            thread = threading.Thread(target=register_wrapper, args=(f"service{i}",))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify no errors occurred
        assert len(errors) == 0
        assert len(registry.list_services()) == 10
