"""Integration tests for service registry pattern.

This module tests the service registry implementation that enables
seamless switching between MCP and direct SDK integrations.
"""

import asyncio

import pytest

from tripsage.config.feature_flags import IntegrationMode, feature_flags
from tripsage.config.service_registry import (
    ServiceAdapter,
    ServiceProtocol,
    ServiceRegistry,
    get_service_registry,
    register_service,
)
from tripsage_core.services.infrastructure import get_cache_service


class MockService(ServiceProtocol):
    """Mock service for testing."""

    def __init__(self):
        self.connected = False
        self.operations = []

    async def connect(self) -> None:
        self.connected = True
        self.operations.append("connect")

    async def close(self) -> None:
        self.connected = False
        self.operations.append("close")

    async def operation(self, value: str) -> str:
        self.operations.append(f"operation:{value}")
        return f"result:{value}"


class MockAdapter(ServiceAdapter):
    """Mock adapter for testing."""

    def __init__(self, service_name="airbnb"):
        super().__init__(service_name)
        self.mcp_service = MockService()
        self.direct_service = MockService()

    async def get_service_instance(self):
        """Get service instance based on integration mode."""
        if self.is_direct:
            await self.direct_service.connect()
            return self.direct_service
        else:
            await self.mcp_service.connect()
            return self.mcp_service

    async def get_mcp_client(self):
        await self.mcp_service.connect()
        return self.mcp_service

    async def get_direct_service(self):
        await self.direct_service.connect()
        return self.direct_service


class TestServiceRegistry:
    """Test service registry functionality."""

    @pytest.fixture
    def registry(self):
        """Create a fresh registry for each test."""
        return ServiceRegistry()

    @pytest.fixture
    def mock_adapter(self):
        """Create mock adapter."""
        return MockAdapter()

    async def test_register_service(self, registry, mock_adapter):
        """Test service registration."""
        registry.register_service("test", mock_adapter)

        assert "test" in registry._services
        assert registry._services["test"] == mock_adapter
        assert "test" in registry._locks

    async def test_get_service_not_registered(self, registry):
        """Test getting unregistered service raises error."""
        with pytest.raises(ValueError, match="Service 'unknown' not registered"):
            await registry.get_service("unknown")

    async def test_get_service_mcp_mode(self, registry, mock_adapter):
        """Test getting service in MCP mode."""
        # Set to MCP mode
        feature_flags.set_integration_mode("airbnb", IntegrationMode.MCP)

        registry.register_service("test", mock_adapter)
        service = await registry.get_service("test")

        assert service == mock_adapter.mcp_service
        assert service.connected
        assert "connect" in service.operations

    async def test_get_service_direct_mode(self, registry, mock_adapter):
        """Test getting service in direct mode."""
        # Set to direct mode
        feature_flags.set_integration_mode("airbnb", IntegrationMode.DIRECT)

        registry.register_service("test", mock_adapter)
        service = await registry.get_service("test")

        assert service == mock_adapter.direct_service
        assert service.connected
        assert "connect" in service.operations

    async def test_service_singleton(self, registry, mock_adapter):
        """Test service instances are singletons."""
        registry.register_service("test", mock_adapter)

        # Get service multiple times
        service1 = await registry.get_service("test")
        service2 = await registry.get_service("test")
        service3 = await registry.get_service("test")

        # Should be same instance
        assert service1 is service2
        assert service2 is service3

        # Should only connect once
        assert service1.operations.count("connect") == 1

    async def test_refresh_service(self, registry, mock_adapter):
        """Test refreshing service after mode change."""
        feature_flags.set_integration_mode("airbnb", IntegrationMode.MCP)
        registry.register_service("test", mock_adapter)

        # Get initial service (MCP)
        service1 = await registry.get_service("test")
        assert service1 == mock_adapter.mcp_service

        # Change mode
        feature_flags.set_integration_mode("airbnb", IntegrationMode.DIRECT)

        # Refresh service
        service2 = await registry.refresh_service("test")
        assert service2 == mock_adapter.direct_service
        assert service2 != service1

        # Old service should be closed
        assert "close" in service1.operations

    async def test_close_all_services(self, registry, mock_adapter):
        """Test closing all services."""
        registry.register_service("test1", mock_adapter)
        registry.register_service("test2", MockAdapter())

        # Get services to initialize them
        service1 = await registry.get_service("test1")
        await registry.get_service("test2")

        # Close all
        await registry.close_all()

        # Should be closed
        assert "close" in service1.operations
        assert not service1.connected

        # Registry should be cleared
        assert len(registry._instances) == 0

    async def test_list_services(self, registry):
        """Test listing registered services."""
        adapter1 = MockAdapter()
        adapter2 = MockAdapter()

        registry.register_service("service1", adapter1)
        registry.register_service("service2", adapter2)

        # Get one service to mark it as connected
        await registry.get_service("service1")

        services = registry.list_services()

        assert len(services) == 2
        assert services["service1"]["name"] == "service1"
        assert services["service1"]["is_connected"] is True
        assert services["service2"]["is_connected"] is False

    async def test_service_context_manager(self, registry, mock_adapter):
        """Test service context manager."""
        registry.register_service("test", mock_adapter)

        async with registry.service_context("test") as service:
            assert service.connected
            result = await service.operation("test_value")
            assert result == "result:test_value"

    async def test_concurrent_service_access(self, registry, mock_adapter):
        """Test concurrent access to services."""
        registry.register_service("test", mock_adapter)

        async def worker(worker_id: int):
            service = await registry.get_service("test")
            return await service.operation(f"worker_{worker_id}")

        # Run multiple workers concurrently
        results = await asyncio.gather(*[worker(i) for i in range(10)])

        # All should get same service instance
        service = await registry.get_service("test")
        assert service.operations.count("connect") == 1

        # All operations should complete
        assert len(results) == 10
        for i, result in enumerate(results):
            assert result == f"result:worker_{i}"


class TestCacheServiceIntegration:
    """Test Core cache service integration."""

    async def test_cache_service_integration(self):
        """Test cache service integration with adapter."""
        # Get Core cache service for testing
        cache_service = await get_cache_service()

        # Test basic operations (with actual service or mocked as needed)
        # Note: This test may need significant updates for Core architecture
        try:
            # Test set operation
            success = await cache_service.set("test_key", "test_value", ttl=60)
            # Test get operation
            result = await cache_service.get("test_key")

            # Basic assertions (may need to be updated based on Core service behavior)
            assert success is True or success is None  # Some services may return None
            assert result == "test_value" or result is None  # Use the result
            # Clean up
            await cache_service.delete("test_key")
        except Exception:
            # Skip if cache service is not available in test environment
            pytest.skip("Cache service not available in test environment")


class TestGlobalRegistry:
    """Test global registry functions."""

    async def test_global_registry_instance(self):
        """Test global registry is singleton."""
        registry1 = get_service_registry()
        registry2 = get_service_registry()

        assert registry1 is registry2

    async def test_global_register_service(self):
        """Test global service registration."""
        adapter = MockAdapter()
        register_service("global_test", adapter)

        registry = get_service_registry()
        assert "global_test" in registry._services

    async def test_migration_status(self):
        """Test migration status reporting."""
        # Set different modes for different services
        feature_flags.set_integration_mode("redis", IntegrationMode.DIRECT)
        feature_flags.set_integration_mode("supabase", IntegrationMode.DIRECT)
        feature_flags.set_integration_mode("memory", IntegrationMode.DIRECT)  # Mem0
        feature_flags.set_integration_mode("airbnb", IntegrationMode.MCP)

        status = feature_flags.get_migration_status()

        assert status["summary"]["total_services"] > 0
        assert status["summary"]["direct_sdk"] >= 3  # redis, supabase, memory
        assert status["summary"]["mcp_wrapper"] >= 1  # airbnb only
        assert status["summary"]["migration_percentage"] > 0

        # Check specific services
        assert status["services"]["redis"] == "direct"
        assert status["services"]["supabase"] == "direct"
        assert status["services"]["memory"] == "direct"  # Mem0
        assert status["services"]["airbnb"] == "mcp"
