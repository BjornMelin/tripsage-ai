"""
Logging middleware for FastAPI.

This middleware logs requests and responses for debugging and monitoring.
"""

import logging
import time
from typing import Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from tripsage_core.config.base_app_settings import settings

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging requests and responses.

    This middleware logs the following information for each request:
    - Request method and path
    - Request headers (in debug mode)
    - Request processing time
    - Response status code
    - Response headers (in debug mode)
    """

    async def dispatch(self, request: Request, call_next):
        """Process the request and log information.

        Args:
            request: The FastAPI request
            call_next: The next middleware or route handler

        Returns:
            The response from the next middleware or route handler
        """
        # Get request ID (from X-Request-ID header if available)
        request_id = request.headers.get("X-Request-ID", "-")

        # Log request start
        start_time = time.time()

        # Log request details (in debug mode)
        client_host = request.client.host if request.client else None
        self._log_request(request, request_id, client_host)

        # Process the request
        try:
            response = await call_next(request)

            # Calculate processing time
            process_time = time.time() - start_time

            # Log response details
            self._log_response(request, response, process_time, request_id)

            return response
        except Exception as e:
            # Log error
            logger.exception(
                f"Request [{request_id}] {request.method} {request.url.path} "
                f"failed after {time.time() - start_time:.4f}s: {str(e)}"
            )
            raise

    def _log_request(
        self,
        request: Request,
        request_id: str,
        client_host: Optional[str],
    ) -> None:
        """Log request details.

        Args:
            request: The FastAPI request
            request_id: The request ID
            client_host: The client host
        """
        # Log basic request information
        logger.info(
            f"Request [{request_id}] {request.method} {request.url.path} "
            f"from {client_host or 'unknown'}"
        )

        # Log headers in debug mode
        if settings.debug:
            headers = "\n".join(f"    {k}: {v}" for k, v in request.headers.items())
            logger.debug(f"Request [{request_id}] headers:\n{headers}")

            # Log query parameters if any
            if request.query_params:
                params = "\n".join(
                    f"    {k}: {v}" for k, v in request.query_params.items()
                )
                logger.debug(f"Request [{request_id}] query params:\n{params}")

    def _log_response(
        self,
        request: Request,
        response: Response,
        process_time: float,
        request_id: str,
    ) -> None:
        """Log response details.

        Args:
            request: The FastAPI request
            response: The FastAPI response
            process_time: The request processing time
            request_id: The request ID
        """
        # Log basic response information
        logger.info(
            f"Response [{request_id}] {request.method} {request.url.path} "
            f"completed with status {response.status_code} in {process_time:.4f}s"
        )

        # Log headers in debug mode
        if settings.debug:
            headers = "\n".join(f"    {k}: {v}" for k, v in response.headers.items())
            logger.debug(f"Response [{request_id}] headers:\n{headers}")
