"""Wrapper implementations for specific MCP clients."""

# Note: Only Airbnb wrapper remains as it has no official SDK
# All other services have been migrated to direct SDK integration

__all__ = [
    "AirbnbMCPWrapper",
    "Crawl4AIMCPWrapper",  # Kept for process isolation benefits
]
