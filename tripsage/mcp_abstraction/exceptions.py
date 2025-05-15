"""
Custom exceptions for the TripSage MCP abstraction layer.

This module defines a hierarchy of exceptions for handling various
MCP-related errors.
"""


class TripSageMCPError(Exception):
    """Base exception for all MCP-related errors in TripSage."""

    pass


class MCPClientError(TripSageMCPError):
    """Exception raised when an MCP client operation fails."""

    def __init__(self, message: str, mcp_name: str, original_error: Exception = None):
        self.mcp_name = mcp_name
        self.original_error = original_error
        super().__init__(message)


class MCPNotFoundError(TripSageMCPError):
    """Exception raised when an MCP is not found."""

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
        original_error: Exception = None,
    ):
        self.method_name = method_name
        super().__init__(message, mcp_name, original_error)


class MCPMethodNotFoundError(MCPClientError):
    """Exception raised when a method is not found on an MCP."""

    def __init__(self, message: str, mcp_name: str = None, method_name: str = None):
        self.method_name = method_name
        super().__init__(message, mcp_name or "unknown")
