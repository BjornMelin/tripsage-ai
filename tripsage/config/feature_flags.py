"""Feature flag system for gradual migration from MCP to direct SDK integration."""

from enum import Enum
from pydantic import Field
from pydantic_settings import BaseSettings


class IntegrationMode(str, Enum):
    """Integration mode for services."""
    
    MCP = "mcp"
    DIRECT = "direct"


class FeatureFlags(BaseSettings):
    """Feature flags for controlling service integration modes.
    
    Set environment variables with FEATURE_ prefix to control modes.
    Example: FEATURE_REDIS_INTEGRATION=direct
    """
    
    # Database services
    redis_integration: IntegrationMode = Field(
        default=IntegrationMode.MCP,
        description="Redis integration mode"
    )
    supabase_integration: IntegrationMode = Field(
        default=IntegrationMode.MCP,
        description="Supabase integration mode"
    )
    
    # Web crawling services
    crawl4ai_integration: IntegrationMode = Field(
        default=IntegrationMode.MCP,
        description="Crawl4AI integration mode"
    )
    playwright_integration: IntegrationMode = Field(
        default=IntegrationMode.MCP,
        description="Playwright integration mode"
    )
    
    # External API services
    weather_integration: IntegrationMode = Field(
        default=IntegrationMode.MCP,
        description="Weather API integration mode"
    )
    maps_integration: IntegrationMode = Field(
        default=IntegrationMode.MCP,
        description="Google Maps integration mode"
    )
    flights_integration: IntegrationMode = Field(
        default=IntegrationMode.MCP,
        description="Duffel Flights integration mode"
    )
    calendar_integration: IntegrationMode = Field(
        default=IntegrationMode.MCP,
        description="Google Calendar integration mode"
    )
    time_integration: IntegrationMode = Field(
        default=IntegrationMode.MCP,
        description="Time service integration mode"
    )

    class Config:
        """Pydantic configuration."""
        
        env_prefix = "FEATURE_"
        case_sensitive = False


# Global feature flags instance
feature_flags = FeatureFlags()