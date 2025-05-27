"""
Custom exceptions for the TripSage MCP abstraction layer.

This module defines a hierarchy of exceptions for handling various
MCP-related errors.
"""

from typing import Optional


class TripSageMCPError(Exception):
    """Base exception for all MCP-related errors in TripSage."""

    pass


# Alias for compatibility
MCPError = TripSageMCPError


class MCPClientError(TripSageMCPError):
    """Exception raised when an MCP client operation fails."""

    def __init__(
        self, message: str, mcp_name: str, original_error: Optional[Exception] = None
    ):
        self.mcp_name = mcp_name
        self.original_error = original_error
        super().__init__(message)


class MCPNotRegisteredError(TripSageMCPError):
    """Exception raised when an MCP is not registered."""

    def __init__(self, message: str, mcp_name: str):
        self.mcp_name = mcp_name
        super().__init__(message)


class MCPManagerError(TripSageMCPError):
    """Exception raised for MCP manager-related errors."""

    pass


class MCPInvocationError(MCPClientError):
    """Exception raised when method invocation fails."""

    def __init__(
        self,
        message: str,
        mcp_name: str,
        method_name: str,
        original_error: Optional[Exception] = None,
    ):
        self.method_name = method_name
        super().__init__(message, mcp_name, original_error)


class MCPMethodNotFoundError(MCPClientError):
    """Exception raised when a method is not found on an MCP."""

    def __init__(
        self,
        message: str,
        mcp_name: Optional[str] = None,
        method_name: Optional[str] = None,
    ):
        self.method_name = method_name
        super().__init__(message, mcp_name or "unknown")


class MCPTimeoutError(MCPClientError):
    """Exception raised when an MCP operation times out."""

    def __init__(
        self,
        message: str,
        mcp_name: str,
        timeout_seconds: float,
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
        mcp_name: str,
        retry_after: Optional[float] = None,
        original_error: Optional[Exception] = None,
    ):
        self.retry_after = retry_after
        super().__init__(message, mcp_name, original_error)


class MCPNotFoundError(MCPClientError):
    """Exception raised when a requested resource is not found in an MCP."""

    def __init__(
        self,
        message: str,
        mcp_name: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ):
        self.resource_type = resource_type
        self.resource_id = resource_id
        super().__init__(message, mcp_name, original_error)
