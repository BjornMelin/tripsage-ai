"""
Error handling middleware for FastAPI.

This middleware handles unexpected exceptions during request processing.
"""

import logging
import traceback
from typing import Dict, Any

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from api.core.config import settings
from api.core.exceptions import TripSageError

logger = logging.getLogger(__name__)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware for handling unexpected exceptions.
    
    This middleware catches any unhandled exceptions during request processing
    and returns a standardized error response. It also logs the error for
    debugging and monitoring.
    """
    
    async def dispatch(self, request: Request, call_next):
        """Process the request and handle errors.
        
        Args:
            request: The FastAPI request
            call_next: The next middleware or route handler
            
        Returns:
            The response from the next middleware or route handler,
            or an error response if an exception occurs
        """
        try:
            # Try to process the request normally
            return await call_next(request)
        except TripSageError as e:
            # Handle known TripSage exceptions
            logger.warning(
                f"TripSageError during request processing: {str(e)} "
                f"[code={e.code}, status={e.status_code}]"
            )
            
            # Create a standardized error response
            return JSONResponse(
                status_code=e.status_code,
                content=self._format_error_response(e.code, str(e), e.details),
            )
        except Exception as e:
            # Handle unexpected exceptions
            logger.exception(f"Unhandled exception during request processing: {str(e)}")
            
            # Create a standardized error response
            # In production, don't include the traceback in the response
            details = self._get_error_details(e) if settings.debug else None
            
            return JSONResponse(
                status_code=500,
                content=self._format_error_response(
                    "INTERNAL_ERROR",
                    "An unexpected error occurred",
                    details,
                ),
            )
    
    def _format_error_response(self, code: str, message: str, details: Dict[str, Any] = None) -> Dict[str, Any]:
        """Format a standardized error response.
        
        Args:
            code: Machine-readable error code
            message: Human-readable error message
            details: Additional error details
            
        Returns:
            Formatted error response
        """
        response = {
            "error": code,
            "message": message,
        }
        
        if details:
            response["details"] = details
            
        return response
    
    def _get_error_details(self, exception: Exception) -> Dict[str, Any]:
        """Get detailed information about an exception.
        
        Args:
            exception: The exception that occurred
            
        Returns:
            Details about the exception
        """
        return {
            "type": type(exception).__name__,
            "traceback": traceback.format_exc(),
        }