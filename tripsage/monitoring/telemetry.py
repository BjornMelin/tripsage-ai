"""OpenTelemetry instrumentation for TripSage AI.

This module provides comprehensive monitoring, tracing, and metrics collection
for the memory service and other critical components.
"""

import os
from collections.abc import Callable
from contextlib import contextmanager
from functools import wraps
from typing import Any

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc import (
    metric_exporter as otlp_metric_exporter,
    trace_exporter as otlp_trace_exporter,
)
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.metrics import CallbackResult, Observation
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.semconv.resource import ResourceAttributes
from opentelemetry.trace import Status, StatusCode

from tripsage_core.config import get_settings
from tripsage_core.utils.logging_utils import get_logger


logger = get_logger(__name__)
settings = get_settings()


class TelemetryService:
    """Centralized telemetry service for monitoring and observability."""

    def __init__(self):
        self.resource = self._create_resource()
        self.tracer_provider = None
        self.meter_provider = None
        self.tracer = None
        self.meter = None
        self._initialized = False

    def _create_resource(self) -> Resource:
        """Create resource with service information."""
        return Resource.create(
            {
                ResourceAttributes.SERVICE_NAME: "tripsage-ai",
                ResourceAttributes.SERVICE_VERSION: os.getenv(
                    "SERVICE_VERSION", "1.0.0"
                ),
                ResourceAttributes.DEPLOYMENT_ENVIRONMENT: settings.environment,
                ResourceAttributes.SERVICE_NAMESPACE: "tripsage",
                ResourceAttributes.SERVICE_INSTANCE_ID: os.getenv("HOSTNAME", "local"),
            }
        )

    def initialize(self) -> None:
        """Initialize OpenTelemetry providers and exporters."""
        if self._initialized:
            return

        try:
            # Initialize tracing
            self._setup_tracing()

            # Initialize metrics
            self._setup_metrics()

            # Auto-instrument Redis/DragonflyDB
            RedisInstrumentor().instrument()

            self._initialized = True
            logger.info("Telemetry service initialized successfully")

        except Exception as e:
            logger.exception(f"Failed to initialize telemetry")

    def _setup_tracing(self) -> None:
        """Set up distributed tracing with OTLP exporter."""
        # Create OTLP trace exporter
        otlp_exporter = otlp_trace_exporter.OTLPSpanExporter(
            endpoint=os.getenv("OTLP_ENDPOINT", "localhost:4317"),
            insecure=True,  # Use TLS in production
        )

        # Create tracer provider
        self.tracer_provider = TracerProvider(resource=self.resource)

        # Add batch processor
        span_processor = BatchSpanProcessor(otlp_exporter)
        self.tracer_provider.add_span_processor(span_processor)

        # Set as global tracer provider
        trace.set_tracer_provider(self.tracer_provider)

        # Get tracer
        self.tracer = trace.get_tracer("tripsage.telemetry", "1.0.0")

    def _setup_metrics(self) -> None:
        """Set up metrics collection with OTLP exporter."""
        # Create OTLP metric exporter
        otlp_exporter = otlp_metric_exporter.OTLPMetricExporter(
            endpoint=os.getenv("OTLP_ENDPOINT", "localhost:4317"),
            insecure=True,  # Use TLS in production
        )

        # Create metric reader
        metric_reader = PeriodicExportingMetricReader(
            exporter=otlp_exporter,
            export_interval_millis=10000,  # Export every 10 seconds
        )

        # Create meter provider
        self.meter_provider = MeterProvider(
            resource=self.resource,
            metric_readers=[metric_reader],
        )

        # Set as global meter provider
        metrics.set_meter_provider(self.meter_provider)

        # Get meter
        self.meter = metrics.get_meter("tripsage.telemetry", "1.0.0")

        # Create standard metrics
        self._create_standard_metrics()

    def _create_standard_metrics(self) -> None:
        """Create standard application metrics."""
        # Memory operation counters
        self.memory_operations_counter = self.meter.create_counter(
            name="memory_operations_total",
            description="Total number of memory operations",
            unit="1",
        )

        # Memory operation duration histogram
        self.memory_operation_duration = self.meter.create_histogram(
            name="memory_operation_duration",
            description="Duration of memory operations",
            unit="ms",
        )

        # Cache hit rate gauge
        self.cache_hit_rate = self.meter.create_gauge(
            name="cache_hit_rate",
            description="Cache hit rate percentage",
            unit="%",
        )

        # Active users gauge
        self.active_users = self.meter.create_up_down_counter(
            name="active_users",
            description="Number of active users",
            unit="1",
        )

        # Memory usage observable gauge
        self.meter.create_observable_gauge(
            name="memory_usage_bytes",
            callbacks=[self._get_memory_usage],
            description="Memory usage in bytes",
            unit="By",
        )

    def _get_memory_usage(self, options: CallbackResult) -> None:
        """Callback for memory usage metric."""
        import psutil

        process = psutil.Process()
        memory_info = process.memory_info()

        yield Observation(value=memory_info.rss, attributes={"type": "rss"})
        yield Observation(value=memory_info.vms, attributes={"type": "vms"})

    @contextmanager
    def span(self, name: str, attributes: dict[str, Any] | None = None):
        """Context manager for creating spans.

        Args:
            name: Span name
            attributes: Optional span attributes

        Example:
            with telemetry.span("search_memories", {"user_id": user_id}):
                # Do work
        """
        if not self.tracer:
            yield None
            return

        with self.tracer.start_as_current_span(name) as span:
            if attributes:
                for key, value in attributes.items():
                    span.set_attribute(key, str(value))

            try:
                yield span
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise

    def record_memory_operation(
        self,
        operation: str,
        duration_ms: float,
        user_id: str,
        success: bool = True,
        error: str | None = None,
    ) -> None:
        """Record memory operation metrics.

        Args:
            operation: Operation name (e.g., "search", "add", "update")
            duration_ms: Operation duration in milliseconds
            user_id: User identifier
            success: Whether operation succeeded
            error: Optional error message
        """
        attributes = {
            "operation": operation,
            "user_id": user_id,
            "success": str(success),
        }

        if error:
            attributes["error"] = error

        # Increment operation counter
        self.memory_operations_counter.add(1, attributes)

        # Record duration
        self.memory_operation_duration.record(duration_ms, attributes)

    def record_cache_hit(self, hit: bool, operation: str) -> None:
        """Record cache hit/miss.

        Args:
            hit: Whether cache hit occurred
            operation: Cache operation type
        """
        attributes = {
            "operation": operation,
            "hit": str(hit),
        }

        # Update cache metrics
        if hasattr(self, "_cache_hits"):
            if hit:
                self._cache_hits += 1
            self._cache_total += 1

            # Update hit rate
            hit_rate = (self._cache_hits / self._cache_total) * 100
            self.cache_hit_rate.set(hit_rate, attributes)
        else:
            self._cache_hits = 1 if hit else 0
            self._cache_total = 1

    def user_session_start(self, user_id: str) -> None:
        """Record user session start."""
        self.active_users.add(1, {"user_id": user_id})

    def user_session_end(self, user_id: str) -> None:
        """Record user session end."""
        self.active_users.add(-1, {"user_id": user_id})

    def create_span_decorator(self, name: str = None):
        """Decorator for automatically creating spans around functions.

        Args:
            name: Optional span name (defaults to function name)

        Example:
            @telemetry.create_span_decorator("process_request")
            async def process_request(request):
                # Function body
        """

        def decorator(func: Callable) -> Callable:
            span_name = name or f"{func.__module__}.{func.__name__}"

            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                with self.span(span_name):
                    return await func(*args, **kwargs)

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                with self.span(span_name):
                    return func(*args, **kwargs)

            # Return appropriate wrapper based on function type
            import asyncio

            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper

        return decorator


# Global telemetry instance
telemetry = TelemetryService()


def initialize_telemetry() -> None:
    """Initialize global telemetry service."""
    telemetry.initialize()


def get_telemetry() -> TelemetryService:
    """Get global telemetry service instance."""
    if not telemetry._initialized:
        telemetry.initialize()
    return telemetry


# Convenience decorators
traced = telemetry.create_span_decorator
