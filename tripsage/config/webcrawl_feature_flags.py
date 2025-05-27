"""
Feature flags for web crawling service migration.

This module provides feature flags to control the migration from MCP-based
crawling to direct Crawl4AI SDK integration.
"""

from dataclasses import dataclass
from typing import List

from pydantic import BaseModel, Field


class WebCrawlFeatureFlags(BaseModel):
    """Feature flags for web crawling operations."""

    # Main feature flag to enable direct Crawl4AI SDK
    use_direct_crawl4ai: bool = Field(
        default=True, description="Enable direct Crawl4AI SDK instead of MCP"
    )

    # Percentage of traffic to route to direct SDK (0-100)
    direct_crawl4ai_percentage: int = Field(
        default=100,
        ge=0,
        le=100,
        description="Percentage of requests to route to direct SDK",
    )

    # Fallback strategy when direct SDK fails
    fallback_to_mcp_on_error: bool = Field(
        default=True, description="Fallback to MCP implementation if direct SDK fails"
    )

    # Domains that should prefer direct SDK
    prefer_direct_for_domains: List[str] = Field(
        default_factory=lambda: [
            "wikipedia.org",
            "github.io",
            "blogspot.com",
            "wordpress.com",
            "medium.com",
            "httpbin.org",  # For testing
        ],
        description="Domains that should use direct SDK when available",
    )

    # Domains that should still use MCP (for compatibility)
    force_mcp_for_domains: List[str] = Field(
        default_factory=lambda: [
            "airbnb.com",  # Keep complex booking sites on MCP initially
            "booking.com",
            "expedia.com",
        ],
        description="Domains that must use MCP implementation",
    )

    # Performance monitoring
    enable_performance_monitoring: bool = Field(
        default=True, description="Enable performance metrics collection for comparison"
    )

    # Debug mode for migration
    debug_migration: bool = Field(
        default=False, description="Enable detailed logging for migration debugging"
    )

    # Timeout for direct SDK operations (seconds)
    direct_sdk_timeout: int = Field(
        default=30, gt=0, description="Timeout for direct SDK operations in seconds"
    )

    # Memory threshold for switching to lightweight mode
    memory_threshold_mb: int = Field(
        default=1000,
        gt=0,
        description="Memory threshold in MB for switching to lightweight mode",
    )

    class Config:
        """Pydantic configuration."""

        env_prefix = "WEBCRAWL_"


@dataclass
class PerformanceMetrics:
    """Performance metrics for comparing implementations."""

    request_count: int = 0
    direct_sdk_success_count: int = 0
    direct_sdk_error_count: int = 0
    mcp_fallback_count: int = 0

    total_direct_sdk_time_ms: float = 0.0
    total_mcp_time_ms: float = 0.0

    avg_direct_sdk_time_ms: float = 0.0
    avg_mcp_time_ms: float = 0.0

    def add_direct_sdk_result(self, duration_ms: float, success: bool):
        """Add a direct SDK result to metrics."""
        self.request_count += 1
        self.total_direct_sdk_time_ms += duration_ms

        if success:
            self.direct_sdk_success_count += 1
        else:
            self.direct_sdk_error_count += 1

        self._update_averages()

    def add_mcp_fallback(self, duration_ms: float):
        """Add an MCP fallback result to metrics."""
        self.mcp_fallback_count += 1
        self.total_mcp_time_ms += duration_ms
        self._update_averages()

    def _update_averages(self):
        """Update average timing calculations."""
        sdk_requests = self.direct_sdk_success_count + self.direct_sdk_error_count
        if sdk_requests > 0:
            self.avg_direct_sdk_time_ms = self.total_direct_sdk_time_ms / sdk_requests

        if self.mcp_fallback_count > 0:
            self.avg_mcp_time_ms = self.total_mcp_time_ms / self.mcp_fallback_count

    @property
    def success_rate(self) -> float:
        """Calculate success rate for direct SDK."""
        total_direct = self.direct_sdk_success_count + self.direct_sdk_error_count
        if total_direct == 0:
            return 0.0
        return self.direct_sdk_success_count / total_direct

    @property
    def performance_improvement(self) -> float:
        """Calculate performance improvement ratio (SDK vs MCP)."""
        if self.avg_mcp_time_ms == 0 or self.avg_direct_sdk_time_ms == 0:
            return 0.0
        return self.avg_mcp_time_ms / self.avg_direct_sdk_time_ms

    def to_dict(self) -> dict:
        """Convert metrics to dictionary for logging/reporting."""
        return {
            "request_count": self.request_count,
            "direct_sdk_success_count": self.direct_sdk_success_count,
            "direct_sdk_error_count": self.direct_sdk_error_count,
            "mcp_fallback_count": self.mcp_fallback_count,
            "avg_direct_sdk_time_ms": round(self.avg_direct_sdk_time_ms, 2),
            "avg_mcp_time_ms": round(self.avg_mcp_time_ms, 2),
            "success_rate": round(self.success_rate * 100, 2),
            "performance_improvement": round(self.performance_improvement, 2),
        }


# Global metrics instance
_performance_metrics = PerformanceMetrics()


def get_performance_metrics() -> PerformanceMetrics:
    """Get the global performance metrics instance."""
    return _performance_metrics


def reset_performance_metrics():
    """Reset performance metrics to initial state."""
    global _performance_metrics
    _performance_metrics = PerformanceMetrics()
