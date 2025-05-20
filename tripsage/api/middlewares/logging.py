"""Logging middleware for FastAPI.

This module provides a middleware for request/response logging in FastAPI,
with structured logging support.
"""

import logging
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging requests and responses.
    
    This middleware logs information about each request and response,
    including timing, status code, and correlation ID.
    """
    
    def __init__(self, app: ASGIApp):
        """Initialize LoggingMiddleware.
        
        Args:
            app: The ASGI application
        """
        super().__init__(app)
    
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Response]
    ) -> Response:
        """Process the request/response and log details.
        
        Args:
            request: The incoming request
            call_next: The next middleware or endpoint handler
            
        Returns:
            The response from the next middleware or endpoint
        """
        # Generate a correlation ID for request tracking
        correlation_id = str(uuid.uuid4())
        request.state.correlation_id = correlation_id
        
        # Log the incoming request
        logger.info(
            f"Request started",
            extra={
                "correlation_id": correlation_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "client_host": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
            },
        )
        
        # Process the request and measure timing
        start_time = time.time()
        try:
            response = await call_next(request)
            
            # Calculate request processing time
            process_time = time.time() - start_time
            
            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = correlation_id
            
            # Log the response
            logger.info(
                f"Request completed: {response.status_code}",
                extra={
                    "correlation_id": correlation_id,
                    "status_code": response.status_code,
                    "processing_time_ms": int(process_time * 1000),
                },
            )
            
            return response
        except Exception as e:
            # Calculate request processing time
            process_time = time.time() - start_time
            
            # Log the exception
            logger.exception(
                f"Request failed: {str(e)}",
                extra={
                    "correlation_id": correlation_id,
                    "processing_time_ms": int(process_time * 1000),
                    "exception": str(e),
                    "exception_type": type(e).__name__,
                },
            )
            raise