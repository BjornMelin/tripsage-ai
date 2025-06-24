"""
OpenTelemetry monitoring setup for TripSage.

This module configures OpenTelemetry for distributed tracing of MCP operations.
"""

import logging
from typing import Optional

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)

logger = logging.getLogger(__name__)


def configure_opentelemetry(
    service_name: str = "tripsage",
    service_version: str = "1.0.0",
    otlp_endpoint: Optional[str] = None,
    use_console_exporter: bool = True,
) -> None:
    """
    Configure OpenTelemetry for the TripSage application.

    Args:
        service_name: Name of the service for tracing
        service_version: Version of the service
        otlp_endpoint: Optional OTLP exporter endpoint
        use_console_exporter: Whether to use console exporter (for development)
    """
    # Create resource identifying the service
    resource = Resource.create(
        {
            SERVICE_NAME: service_name,
            SERVICE_VERSION: service_version,
        }
    )

    # Create tracer provider
    provider = TracerProvider(resource=resource)

    # Configure exporters
    if use_console_exporter:
        # Use console exporter for development
        console_exporter = ConsoleSpanExporter()
        provider.add_span_processor(SimpleSpanProcessor(console_exporter))
        logger.info("Console exporter configured for OpenTelemetry")

    if otlp_endpoint:
        # Configure OTLP exporter for production
        otlp_exporter = OTLPSpanExporter(
            endpoint=otlp_endpoint,
            headers=None,  # Add authentication headers if needed
        )
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
        logger.info(f"OTLP exporter configured for endpoint: {otlp_endpoint}")

    # Set the global tracer provider
    trace.set_tracer_provider(provider)

    logger.info(
        f"OpenTelemetry configured for service '{service_name}' version '{service_version}'"
    )


def get_tracer(component_name: str) -> trace.Tracer:
    """
    Get a tracer for a specific component.

    Args:
        component_name: Name of the component (usually __name__)

    Returns:
        A tracer instance for the component
    """
    return trace.get_tracer(component_name)
