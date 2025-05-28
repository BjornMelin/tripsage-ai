"""Service Registry for unified service discovery and configuration.

This module provides a lightweight registry pattern for managing service instances
with support for different integration modes (direct SDK, API, etc).
"""

import asyncio
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import Any, Dict, Protocol

from tripsage.config.app_settings import get_settings
from tripsage.config.feature_flags import IntegrationMode, feature_flags


class ServiceProtocol(Protocol):
    """Protocol for service implementations."""

    async def connect(self) -> None:
        """Initialize service connection."""
        ...

    async def close(self) -> None:
        """Close service connection."""
        ...


class BaseService(ABC):
    """Base class for all service implementations."""

    def __init__(self):
        self.settings = get_settings()
        self._connected = False

    @abstractmethod
    async def connect(self) -> None:
        """Initialize service connection."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close service connection."""
        pass

    @property
    def is_connected(self) -> bool:
        """Check if service is connected."""
        return self._connected


class ServiceAdapter(ABC):
    """Abstract adapter for services supporting different integration modes."""

    def __init__(self, service_name: str):
        self.service_name = service_name
        self._service_instance = None

    @property
    def integration_mode(self) -> IntegrationMode:
        """Get current integration mode for this service."""
        return feature_flags.get_integration_mode(self.service_name)

    @property
    def is_direct(self) -> bool:
        """Check if using direct SDK integration."""
        return self.integration_mode == IntegrationMode.DIRECT

    @abstractmethod
    async def get_service_instance(self):
        """Get service instance."""
        pass

    async def get_service(self):
        """Get appropriate service instance."""
        return await self.get_service_instance()


class ServiceRegistry:
    """Lightweight service registry for unified service discovery.

    Replaces the complex MCP Manager with a simpler pattern that supports
    both MCP wrappers and direct SDK integration during migration.
    """

    def __init__(self):
        self._services: Dict[str, ServiceAdapter] = {}
        self._instances: Dict[str, Any] = {}
        self._locks: Dict[str, asyncio.Lock] = {}

    def register_service(self, name: str, adapter: ServiceAdapter) -> None:
        """Register a service adapter.

        Args:
            name: Service name
            adapter: Service adapter instance
        """
        self._services[name] = adapter
        self._locks[name] = asyncio.Lock()

    async def get_service(self, name: str) -> Any:
        """Get service instance by name.

        Args:
            name: Service name

        Returns:
            Service instance (MCP client or direct service)

        Raises:
            ValueError: If service is not registered
        """
        if name not in self._services:
            raise ValueError(f"Service '{name}' not registered")

        # Thread-safe singleton pattern
        async with self._locks[name]:
            if name not in self._instances:
                adapter = self._services[name]
                self._instances[name] = await adapter.get_service()

            return self._instances[name]

    async def refresh_service(self, name: str) -> Any:
        """Refresh service instance (useful after feature flag changes).

        Args:
            name: Service name

        Returns:
            New service instance
        """
        async with self._locks[name]:
            # Close existing instance if it exists
            if name in self._instances:
                old_instance = self._instances[name]
                if hasattr(old_instance, "close"):
                    try:
                        await old_instance.close()
                    except Exception:
                        pass  # Ignore cleanup errors

                del self._instances[name]

            # Create new instance
            adapter = self._services[name]
            self._instances[name] = await adapter.get_service()
            return self._instances[name]

    async def close_all(self) -> None:
        """Close all service connections."""
        for _name, instance in self._instances.items():
            if hasattr(instance, "close"):
                try:
                    await instance.close()
                except Exception:
                    pass  # Ignore cleanup errors

        self._instances.clear()

    def list_services(self) -> Dict[str, Dict[str, Any]]:
        """List all registered services and their status.

        Returns:
            Dictionary with service information
        """
        services = {}
        for name, adapter in self._services.items():
            services[name] = {
                "name": name,
                "integration_mode": adapter.integration_mode.value,
                "is_connected": name in self._instances,
                "adapter_type": type(adapter).__name__,
            }

        return services

    @asynccontextmanager
    async def service_context(self, name: str):
        """Context manager for service usage.

        Args:
            name: Service name

        Yields:
            Service instance

        Example:
            async with registry.service_context('redis') as redis:
                await redis.set('key', 'value')
        """
        service = await self.get_service(name)
        try:
            yield service
        finally:
            # Services are managed by the registry, no cleanup needed here
            pass


# Global service registry instance
service_registry = ServiceRegistry()


def get_service_registry() -> ServiceRegistry:
    """Get the global service registry instance.

    Returns:
        Global ServiceRegistry instance
    """
    return service_registry


async def get_service(name: str) -> Any:
    """Convenience function to get a service from the global registry.

    Args:
        name: Service name

    Returns:
        Service instance
    """
    return await service_registry.get_service(name)


async def refresh_service(name: str) -> Any:
    """Convenience function to refresh a service in the global registry.

    Args:
        name: Service name

    Returns:
        New service instance
    """
    return await service_registry.refresh_service(name)


def register_service(name: str, adapter: ServiceAdapter) -> None:
    """Convenience function to register a service in the global registry.

    Args:
        name: Service name
        adapter: Service adapter instance
    """
    service_registry.register_service(name, adapter)


async def close_all_services() -> None:
    """Convenience function to close all services in the global registry."""
    await service_registry.close_all()
