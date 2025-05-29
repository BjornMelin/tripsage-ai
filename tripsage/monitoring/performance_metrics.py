"""
Performance tracking for all TripSage services.

This module provides comprehensive performance metrics tracking to monitor
service reliability and response times across all integrations.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional


@dataclass
class ServiceMetrics:
    """Performance metrics for a specific service."""

    service_name: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_duration_ms: float = 0.0
    average_duration_ms: float = 0.0
    last_updated: datetime = field(default_factory=datetime.now)

    # Service-specific metrics
    custom_metrics: Dict[str, float] = field(default_factory=dict)

    def add_request_result(self, duration_ms: float, success: bool) -> None:
        """Record a service request result.

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
        self.last_updated = datetime.now()

    def add_custom_metric(self, metric_name: str, value: float) -> None:
        """Add a custom metric for this service.

        Args:
            metric_name: Name of the custom metric
            value: Value to record
        """
        if metric_name not in self.custom_metrics:
            self.custom_metrics[metric_name] = 0.0
        self.custom_metrics[metric_name] += value

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100

    @property
    def error_rate(self) -> float:
        """Calculate error rate as percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.failed_requests / self.total_requests) * 100

    def get_summary(self) -> dict:
        """Get performance summary."""
        return {
            "service_name": self.service_name,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate_percent": round(self.success_rate, 2),
            "error_rate_percent": round(self.error_rate, 2),
            "average_duration_ms": round(self.average_duration_ms, 2),
            "total_duration_ms": round(self.total_duration_ms, 2),
            "last_updated": self.last_updated.isoformat(),
            "custom_metrics": self.custom_metrics,
        }


@dataclass
class PerformanceMetrics:
    """Central performance metrics for all services."""

    services: Dict[str, ServiceMetrics] = field(default_factory=dict)

    def get_service_metrics(self, service_name: str) -> ServiceMetrics:
        """Get or create metrics for a service.

        Args:
            service_name: Name of the service

        Returns:
            ServiceMetrics instance for the service
        """
        if service_name not in self.services:
            self.services[service_name] = ServiceMetrics(service_name=service_name)
        return self.services[service_name]

    def record_request(
        self, service_name: str, duration_ms: float, success: bool
    ) -> None:
        """Record a request for a service.

        Args:
            service_name: Name of the service
            duration_ms: Duration in milliseconds
            success: Whether the request succeeded
        """
        metrics = self.get_service_metrics(service_name)
        metrics.add_request_result(duration_ms, success)

    def record_custom_metric(
        self, service_name: str, metric_name: str, value: float
    ) -> None:
        """Record a custom metric for a service.

        Args:
            service_name: Name of the service
            metric_name: Name of the custom metric
            value: Value to record
        """
        metrics = self.get_service_metrics(service_name)
        metrics.add_custom_metric(metric_name, value)

    def get_all_summaries(self) -> Dict[str, dict]:
        """Get summaries for all services."""
        return {
            service_name: metrics.get_summary()
            for service_name, metrics in self.services.items()
        }

    def get_summary(self, service_name: str) -> Optional[dict]:
        """Get summary for a specific service.

        Args:
            service_name: Name of the service

        Returns:
            Summary dict or None if service not found
        """
        if service_name in self.services:
            return self.services[service_name].get_summary()
        return None

    def reset_service(self, service_name: str) -> None:
        """Reset metrics for a specific service.

        Args:
            service_name: Name of the service to reset
        """
        if service_name in self.services:
            self.services[service_name] = ServiceMetrics(service_name=service_name)

    def reset_all(self) -> None:
        """Reset all metrics."""
        self.services.clear()


# Global performance metrics instance
_performance_metrics: Optional[PerformanceMetrics] = None


def get_performance_metrics() -> PerformanceMetrics:
    """Get the global performance metrics instance."""
    global _performance_metrics
    if _performance_metrics is None:
        _performance_metrics = PerformanceMetrics()
    return _performance_metrics


def reset_performance_metrics() -> None:
    """Reset all performance metrics (useful for testing)."""
    global _performance_metrics
    _performance_metrics = PerformanceMetrics()


# Convenience functions for common services
def record_webcrawl_request(duration_ms: float, success: bool) -> None:
    """Record a webcrawl request."""
    get_performance_metrics().record_request("webcrawl", duration_ms, success)


def record_api_request(api_name: str, duration_ms: float, success: bool) -> None:
    """Record an API request.

    Args:
        api_name: Name of the API (e.g., "duffel", "google_maps")
        duration_ms: Duration in milliseconds
        success: Whether the request succeeded
    """
    get_performance_metrics().record_request(f"api_{api_name}", duration_ms, success)


def record_database_request(operation: str, duration_ms: float, success: bool) -> None:
    """Record a database request.

    Args:
        operation: Type of operation (e.g., "select", "insert")
        duration_ms: Duration in milliseconds
        success: Whether the request succeeded
    """
    metrics = get_performance_metrics()
    metrics.record_request("database", duration_ms, success)
    metrics.record_custom_metric("database", f"operation_{operation}", 1)
