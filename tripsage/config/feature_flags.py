"""Feature flags for gradual MCP to SDK migration rollout.

This module provides feature flag management for safely migrating from MCP wrappers
to direct SDK integration with zero-downtime deployment and instant rollback capability.
"""

from enum import Enum
from typing import Any, Dict

from pydantic import Field
from pydantic_settings import BaseSettings


class IntegrationMode(str, Enum):
    """Integration mode for service implementations."""

    MCP = "mcp"
    DIRECT = "direct"


class FeatureFlags(BaseSettings):
    """Feature flags for MCP to SDK migration.

    Each service can be independently switched between MCP wrapper and direct SDK
    integration using environment variables prefixed with FEATURE_.

    Example usage:
        export FEATURE_REDIS_INTEGRATION=direct
        export FEATURE_SUPABASE_INTEGRATION=mcp
    """

    # Infrastructure Services (Week 1)
    redis_integration: IntegrationMode = Field(
        default=IntegrationMode.MCP, description="Redis/DragonflyDB integration mode"
    )

    # Database Services (Week 2)
    supabase_integration: IntegrationMode = Field(
        default=IntegrationMode.MCP, description="Supabase database integration mode"
    )
    neo4j_integration: IntegrationMode = Field(
        default=IntegrationMode.MCP,
        description="Neo4j memory/knowledge graph integration mode",
    )
    memory_integration: IntegrationMode = Field(
        default=IntegrationMode.DIRECT,
        description="Memory system integration mode (Mem0 direct SDK)",
    )

    # Web Crawling Services (Week 3) - Already completed per docs
    crawl4ai_integration: IntegrationMode = Field(
        default=IntegrationMode.DIRECT,
        description="Crawl4AI web crawling integration mode",
    )
    playwright_integration: IntegrationMode = Field(
        default=IntegrationMode.DIRECT,
        description="Playwright browser automation integration mode",
    )

    # External API Services (Week 4)
    weather_integration: IntegrationMode = Field(
        default=IntegrationMode.MCP, description="Weather API integration mode"
    )
    maps_integration: IntegrationMode = Field(
        default=IntegrationMode.DIRECT,
        description="Google Maps integration mode (Direct SDK only)",
    )
    flights_integration: IntegrationMode = Field(
        default=IntegrationMode.MCP, description="Duffel Flights integration mode"
    )
    calendar_integration: IntegrationMode = Field(
        default=IntegrationMode.MCP, description="Google Calendar integration mode"
    )
    time_integration: IntegrationMode = Field(
        default=IntegrationMode.MCP, description="Time service integration mode"
    )

    # Services keeping MCP (according to migration plan)
    airbnb_integration: IntegrationMode = Field(
        default=IntegrationMode.MCP,
        description="Airbnb integration mode (stays MCP due to unofficial API)",
    )

    class Config:
        """Pydantic configuration."""

        env_prefix = "FEATURE_"
        case_sensitive = False

    def get_integration_mode(self, service_name: str) -> IntegrationMode:
        """Get integration mode for a specific service.

        Args:
            service_name: Name of the service (e.g., 'redis', 'supabase')

        Returns:
            IntegrationMode for the service

        Raises:
            ValueError: If service_name is not supported
        """
        field_name = f"{service_name}_integration"
        if hasattr(self, field_name):
            return getattr(self, field_name)
        raise ValueError(f"Service '{service_name}' not supported")

    def set_integration_mode(self, service_name: str, mode: IntegrationMode) -> None:
        """Set integration mode for a specific service.

        Args:
            service_name: Name of the service (e.g., 'redis', 'supabase')
            mode: Integration mode to set

        Raises:
            ValueError: If service_name is not supported
        """
        field_name = f"{service_name}_integration"
        if hasattr(self, field_name):
            setattr(self, field_name, mode)
        else:
            raise ValueError(f"Service '{service_name}' not supported")

    def get_migration_status(self) -> Dict[str, Any]:
        """Get current migration status for all services.

        Returns:
            Dictionary with migration status information
        """
        services = {}
        direct_count = 0
        mcp_count = 0

        for field_name in self.__class__.model_fields:
            if field_name.endswith("_integration"):
                service_name = field_name.replace("_integration", "")
                mode = getattr(self, field_name)
                services[service_name] = mode.value

                if mode == IntegrationMode.DIRECT:
                    direct_count += 1
                else:
                    mcp_count += 1

        total_services = direct_count + mcp_count
        migration_percentage = (
            (direct_count / total_services * 100) if total_services > 0 else 0
        )

        return {
            "services": services,
            "summary": {
                "total_services": total_services,
                "direct_sdk": direct_count,
                "mcp_wrapper": mcp_count,
                "migration_percentage": round(migration_percentage, 1),
            },
        }


# Global feature flags instance
feature_flags = FeatureFlags()


def get_feature_flags() -> FeatureFlags:
    """Get the global feature flags instance.

    Returns:
        Global FeatureFlags instance
    """
    return feature_flags


def is_direct_integration(service_name: str) -> bool:
    """Check if a service is using direct SDK integration.

    Args:
        service_name: Name of the service to check

    Returns:
        True if using direct integration, False if using MCP
    """
    try:
        mode = feature_flags.get_integration_mode(service_name)
        return mode == IntegrationMode.DIRECT
    except ValueError:
        # Default to MCP for unknown services
        return False


def enable_direct_integration(service_name: str) -> None:
    """Enable direct SDK integration for a service.

    Args:
        service_name: Name of the service to enable direct integration for
    """
    feature_flags.set_integration_mode(service_name, IntegrationMode.DIRECT)


def enable_mcp_integration(service_name: str) -> None:
    """Enable MCP wrapper integration for a service.

    Args:
        service_name: Name of the service to enable MCP integration for
    """
    feature_flags.set_integration_mode(service_name, IntegrationMode.MCP)
