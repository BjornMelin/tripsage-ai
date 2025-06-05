"""
Custom exceptions for the Airbnb MCP abstraction layer.

This module defines exceptions for handling Airbnb MCP-related errors.
"""

from typing import Optional


class TripSageMCPError(Exception):
    """Base exception for MCP-related errors in TripSage."""

    pass


class MCPClientError(TripSageMCPError):
    """Exception raised when an MCP client operation fails."""

    def __init__(
        self,
        message: str,
        mcp_name: str = "airbnb",
        original_error: Optional[Exception] = None,
    ):
        self.mcp_name = mcp_name
        self.original_error = original_error
        super().__init__(message)


class MCPRegistrationError(TripSageMCPError):
    """Exception raised for MCP registration errors."""

    pass


class MCPInvocationError(MCPClientError):
    """Exception raised when method invocation fails."""

    def __init__(
        self,
        message: str,
        mcp_name: str = "airbnb",
        method_name: str = "",
        original_error: Optional[Exception] = None,
    ):
        self.method_name = method_name
        super().__init__(message, mcp_name, original_error)


class MCPMethodNotFoundError(MCPClientError):
    """Exception raised when a method is not found on the MCP."""

    def __init__(
        self,
        message: str,
        mcp_name: str = "airbnb",
        method_name: str = "",
    ):
        self.method_name = method_name
        super().__init__(message, mcp_name)


class MCPTimeoutError(MCPClientError):
    """Exception raised when an MCP operation times out."""

    def __init__(
        self,
        message: str,
        mcp_name: str = "airbnb",
        timeout_seconds: float = 30.0,
        original_error: Optional[Exception] = None,
    ):
        self.timeout_seconds = timeout_seconds
        super().__init__(message, mcp_name, original_error)


class MCPAuthenticationError(MCPClientError):
    """Exception raised when MCP authentication fails."""

    pass


class MCPRateLimitError(MCPClientError):
    """Exception raised when MCP rate limits are exceeded."""

    def __init__(
        self,
        message: str,
        mcp_name: str = "airbnb",
        retry_after: Optional[float] = None,
        original_error: Optional[Exception] = None,
    ):
        self.retry_after = retry_after
        super().__init__(message, mcp_name, original_error)
