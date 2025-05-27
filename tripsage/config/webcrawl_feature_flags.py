"""
Performance tracking for optimized Crawl4AI SDK integration.

This module provides performance metrics tracking for the direct Crawl4AI SDK
implementation to monitor the 2-3x performance improvements.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class PerformanceMetrics:
    """Performance metrics for direct SDK operations."""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_duration_ms: float = 0.0
    average_duration_ms: float = 0.0

    # Playwright fallback tracking
    playwright_fallback_attempts: int = 0
    playwright_fallback_successes: int = 0

    def add_direct_sdk_result(self, duration_ms: float, success: bool) -> None:
        """Record a direct SDK operation result.

        Args:
            duration_ms: Duration of the operation in milliseconds
            success: Whether the operation was successful
        """
        self.total_requests += 1
        self.total_duration_ms += duration_ms

        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1

        # Update average
        self.average_duration_ms = self.total_duration_ms / self.total_requests

    def add_playwright_fallback_result(self, success: bool) -> None:
        """Record a Playwright fallback operation result.

        Args:
            success: Whether the fallback operation was successful
        """
        self.playwright_fallback_attempts += 1

        if success:
            self.playwright_fallback_successes += 1

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100

    @property
    def playwright_fallback_success_rate(self) -> float:
        """Calculate Playwright fallback success rate as percentage."""
        if self.playwright_fallback_attempts == 0:
            return 0.0
        return (
            self.playwright_fallback_successes / self.playwright_fallback_attempts
        ) * 100

    def get_summary(self) -> dict:
        """Get performance summary."""
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate_percent": self.success_rate,
            "average_duration_ms": self.average_duration_ms,
            "total_duration_ms": self.total_duration_ms,
            "playwright_fallback_attempts": self.playwright_fallback_attempts,
            "playwright_fallback_successes": self.playwright_fallback_successes,
            "playwright_fallback_success_rate_percent": (
                self.playwright_fallback_success_rate
            ),
        }


# Global performance metrics instance
_performance_metrics: Optional[PerformanceMetrics] = None


def get_performance_metrics() -> PerformanceMetrics:
    """Get the global performance metrics instance."""
    global _performance_metrics
    if _performance_metrics is None:
        _performance_metrics = PerformanceMetrics()
    return _performance_metrics


def reset_performance_metrics() -> None:
    """Reset performance metrics (useful for testing)."""
    global _performance_metrics
    _performance_metrics = PerformanceMetrics()
