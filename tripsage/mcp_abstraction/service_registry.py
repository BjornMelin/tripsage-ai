"""
MCP Service Registry

Dynamic MCP server management with health checking, auto-discovery,
and lifecycle management.
"""

import asyncio
import json
import logging
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from tripsage.config.mcp_settings import MCPSettings
from tripsage.mcp_abstraction.exceptions import TripSageMCPError
from tripsage.mcp_abstraction.registry import MCPClientRegistry


class ServiceStatus(str, Enum):
    """MCP service status enumeration"""

    UNKNOWN = "unknown"
    STARTING = "starting"
    RUNNING = "running"
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class MCPServiceInfo(BaseModel):
    """Information about a registered MCP service"""

    name: str
    wrapper_class: str
    status: ServiceStatus = ServiceStatus.UNKNOWN
    last_health_check: Optional[datetime] = None
    error_count: int = 0
    metadata: Dict[str, str] = Field(default_factory=dict)


class MCPServiceRegistry:
    """
    Dynamic MCP server management registry.

    Handles service discovery, health checking, and lifecycle management
    for all MCP servers in the TripSage ecosystem.
    """

    def __init__(self, settings: Optional[MCPSettings] = None):
        self.settings = settings or MCPSettings()
        self.services: Dict[str, MCPServiceInfo] = {}
        self.health_check_interval = 60  # seconds
        self.max_error_count = 3
        self.logger = logging.getLogger(__name__)
        self._health_check_task: Optional[asyncio.Task] = None
        self._registry = MCPClientRegistry()

    async def initialize(self):
        """Initialize the service registry"""
        await self.discover_services()
        self._health_check_task = asyncio.create_task(self._health_check_loop())

    async def shutdown(self):
        """Shut down the service registry"""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

    async def register_service(self, name: str, wrapper_class: str) -> MCPServiceInfo:
        """Register a new MCP service"""
        if name in self.services:
            self.logger.warning(f"Service {name} already registered")
            return self.services[name]

        service = MCPServiceInfo(name=name, wrapper_class=wrapper_class)
        self.services[name] = service
        self.logger.info(f"Registered service: {name}")

        # Perform initial health check
        await self.health_check(name)
        return service

    async def unregister_service(self, name: str) -> bool:
        """Unregister an MCP service"""
        if name not in self.services:
            self.logger.warning(f"Service {name} not found")
            return False

        del self.services[name]
        self.logger.info(f"Unregistered service: {name}")
        return True

    async def discover_services(self) -> List[str]:
        """Auto-discover available MCP servers"""
        discovered = []

        # Discover from registered wrappers
        for wrapper_name, wrapper_class in self._registry.registry.items():
            if wrapper_name not in self.services:
                await self.register_service(wrapper_name, wrapper_class.__name__)
                discovered.append(wrapper_name)

        self.logger.info(f"Discovered {len(discovered)} new services")
        return discovered

    async def health_check(self, service_name: str) -> bool:
        """Check if a service is responsive"""
        if service_name not in self.services:
            self.logger.error(f"Service {service_name} not found")
            return False

        service = self.services[service_name]
        service.status = ServiceStatus.RUNNING

        try:
            # Get wrapper instance
            wrapper = self._registry.get_wrapper(service_name)

            # Attempt a simple ping or list operation
            if hasattr(wrapper, "ping"):
                await wrapper.ping()
            elif hasattr(wrapper, "list_tools"):
                await wrapper.list_tools()
            else:
                # Fallback to checking if service is registered
                if service_name in self._registry.registry:
                    service.status = ServiceStatus.HEALTHY
                else:
                    raise TripSageMCPError(
                        f"No health check method available for {service_name}"
                    )

            service.status = ServiceStatus.HEALTHY
            service.error_count = 0
            service.last_health_check = datetime.now()
            return True

        except Exception as e:
            self.logger.error(f"Health check failed for {service_name}: {e}")
            service.error_count += 1

            if service.error_count >= self.max_error_count:
                service.status = ServiceStatus.UNHEALTHY
            else:
                service.status = ServiceStatus.ERROR

            service.last_health_check = datetime.now()
            return False

    async def get_healthy_services(self) -> List[str]:
        """Get list of healthy services"""
        healthy = []
        for name, service in self.services.items():
            if service.status == ServiceStatus.HEALTHY:
                healthy.append(name)
        return healthy

    async def get_service_status(self, service_name: str) -> Optional[MCPServiceInfo]:
        """Get status information for a service"""
        return self.services.get(service_name)

    async def get_all_statuses(self) -> Dict[str, MCPServiceInfo]:
        """Get status information for all services"""
        return self.services.copy()

    async def _health_check_loop(self):
        """Background task to periodically check service health"""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)

                # Check all services
                for service_name in list(self.services.keys()):
                    try:
                        await self.health_check(service_name)
                    except Exception as e:
                        self.logger.error(
                            f"Error during health check for {service_name}: {e}"
                        )

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in health check loop: {e}")

    def to_dict(self) -> Dict[str, Dict[str, str]]:
        """Export registry state as dictionary"""
        export = {}
        for name, service in self.services.items():
            export[name] = {
                "wrapper_class": service.wrapper_class,
                "status": service.status,
                "last_health_check": (
                    service.last_health_check.isoformat()
                    if service.last_health_check
                    else None
                ),
                "error_count": str(service.error_count),
                **service.metadata,
            }
        return export

    def to_json(self) -> str:
        """Export registry state as JSON"""
        return json.dumps(self.to_dict(), indent=2)

    def save_state(self, filepath: Path):
        """Save registry state to file"""
        with open(filepath, "w") as f:
            f.write(self.to_json())

    def load_state(self, filepath: Path):
        """Load registry state from file"""
        if not filepath.exists():
            self.logger.warning(f"State file not found: {filepath}")
            return

        try:
            with open(filepath, "r") as f:
                data = json.load(f)

            for name, info in data.items():
                service = MCPServiceInfo(
                    name=name,
                    wrapper_class=info["wrapper_class"],
                    status=ServiceStatus(info["status"]),
                    last_health_check=(
                        datetime.fromisoformat(info["last_health_check"])
                        if info["last_health_check"]
                        else None
                    ),
                    error_count=int(info.get("error_count", 0)),
                    metadata={
                        k: v
                        for k, v in info.items()
                        if k
                        not in [
                            "wrapper_class",
                            "status",
                            "last_health_check",
                            "error_count",
                        ]
                    },
                )
                self.services[name] = service

            self.logger.info(f"Loaded state for {len(self.services)} services")

        except Exception as e:
            self.logger.error(f"Failed to load state from {filepath}: {e}")


# Global service registry instance
service_registry = MCPServiceRegistry()


async def get_service_registry() -> MCPServiceRegistry:
    """Get the global service registry instance"""
    if not service_registry._health_check_task:
        await service_registry.initialize()
    return service_registry
