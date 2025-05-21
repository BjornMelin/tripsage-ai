"""Metrics middleware for the TripSage API.

This module provides middleware for collecting metrics in FastAPI applications.
"""

import logging
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware for collecting API metrics."""

    def __init__(self, app: ASGIApp):
        """Initialize the MetricsMiddleware.

        Args:
            app: The ASGI application
        """
        super().__init__(app)
        logger.info("Metrics middleware initialized")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request and collect metrics.

        Args:
            request: The incoming request
            call_next: The next middleware or endpoint handler

        Returns:
            The response from the next middleware or endpoint
        """
        # Record start time
        start_time = time.time()

        # Process the request
        response = await call_next(request)

        # Calculate request duration
        duration = time.time() - start_time

        # Log metrics (placeholder for actual metrics collection)
        logger.debug(
            f"Request {request.method} {request.url.path} completed in {duration:.3f}s "
            f"with status {response.status_code}"
        )

        return response
