"""
Simplified MCP Manager for Airbnb accommodation operations.

This module provides a streamlined manager that handles the single remaining
MCP integration for Airbnb accommodations.
"""

import logging
from typing import Any, Dict, Optional

from .exceptions import (
    MCPAuthenticationError,
    MCPInvocationError,
    MCPMethodNotFoundError,
    MCPRateLimitError,
    MCPTimeoutError,
)
from .wrappers import AirbnbMCPWrapper

logger = logging.getLogger(__name__)


class MCPManager:
    """Manager for Airbnb MCP operations."""

    def __init__(self):
        """Initialize the MCP manager."""
        self._wrapper: Optional[AirbnbMCPWrapper] = None

    async def initialize(self) -> AirbnbMCPWrapper:
        """
        Initialize the Airbnb MCP wrapper.

        Returns:
            The initialized Airbnb wrapper

        Raises:
            MCPInvocationError: If initialization fails
        """
        if self._wrapper is not None:
            return self._wrapper

        try:
            self._wrapper = AirbnbMCPWrapper()
            logger.info("Initialized Airbnb MCP wrapper")
            return self._wrapper
        except Exception as e:
            logger.error(f"Failed to initialize Airbnb MCP: {e}")
            raise MCPInvocationError(
                f"Failed to initialize Airbnb MCP: {str(e)}",
                mcp_name="airbnb",
                method_name="initialize",
                original_error=e,
            ) from e

    async def invoke(
        self,
        method_name: str = None,
        params: Optional[Dict[str, Any]] = None,
        mcp_name: Optional[str] = None,
        **kwargs,
    ) -> Any:
        """
        Invoke a method on the Airbnb MCP.

        Args:
            method_name: The method to invoke
            params: Method parameters as a dictionary
            mcp_name: For backward compatibility only. Must be 'airbnb' if provided.
            **kwargs: Additional keyword arguments

        Returns:
            The result from the MCP method call

        Raises:
            MCPInvocationError: If the invocation fails
        """
        # Handle backward compatibility with old API
        if mcp_name is not None:
            if mcp_name != "airbnb":
                raise MCPInvocationError(
                    f"MCP '{mcp_name}' is not supported. Only 'airbnb' remains after SDK migration.",
                    mcp_name=mcp_name,
                    method_name=method_name or "",
                )
            # If mcp_name is airbnb and method_name is in kwargs, extract it
            if method_name is None and "method_name" in kwargs:
                method_name = kwargs.pop("method_name")
        
        if method_name is None:
            raise MCPInvocationError(
                "method_name is required",
                mcp_name="airbnb",
                method_name="",
            )
        logger.info(f"Invoking Airbnb MCP method: {method_name}")

        try:
            # Initialize if not already done
            if self._wrapper is None:
                await self.initialize()

            # Prepare parameters
            call_params = params or {}
            call_params.update(kwargs)

            # Invoke the method
            result = await self._wrapper.invoke_method(method_name, **call_params)

            logger.info(f"Successfully invoked Airbnb MCP method: {method_name}")
            return result

        except Exception as e:
            error_msg = f"Failed to invoke airbnb.{method_name}: {str(e)}"
            logger.error(error_msg)

            # Map to specific exception types if possible
            if isinstance(e, TimeoutError) or "timeout" in str(e).lower():
                raise MCPTimeoutError(
                    error_msg,
                    mcp_name="airbnb",
                    timeout_seconds=30,
                    original_error=e,
                ) from e
            elif "401" in str(e) or "unauthorized" in str(e).lower():
                raise MCPAuthenticationError(
                    error_msg, mcp_name="airbnb", original_error=e
                ) from e
            elif "429" in str(e) or "rate limit" in str(e).lower():
                raise MCPRateLimitError(
                    error_msg, mcp_name="airbnb", original_error=e
                ) from e
            elif "not found" in str(e).lower() or "unknown method" in str(e).lower():
                raise MCPMethodNotFoundError(
                    error_msg, mcp_name="airbnb", method_name=method_name
                ) from e
            else:
                raise MCPInvocationError(
                    error_msg,
                    mcp_name="airbnb",
                    method_name=method_name,
                    original_error=e,
                ) from e

    def get_available_methods(self) -> list[str]:
        """
        Get list of available methods for the Airbnb MCP.

        Returns:
            List of available method names
        """
        if self._wrapper is None:
            # Return the standard methods without initializing
            return [
                "search_listings",
                "search_accommodations",
                "search",
                "get_listing_details",
                "get_listing",
                "get_details",
                "get_accommodation_details",
                "check_availability",
                "check_listing_availability",
            ]
        return self._wrapper.get_available_methods()


# Global manager instance
mcp_manager = MCPManager()
