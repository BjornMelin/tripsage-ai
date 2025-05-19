"""
Tests for MCP exception hierarchy - isolated version.

Tests custom exception classes used throughout the MCP abstraction layer.
"""

# Setup environment variables before imports
import os

os.environ["REDIS_URL"] = "redis://localhost:6379/0"

# Setup mocks before any imports
import sys
from unittest.mock import MagicMock

# Mock the problematic modules
sys.modules["tripsage.config.app_settings"] = MagicMock()
sys.modules["tripsage.utils.settings"] = MagicMock()
sys.modules["tripsage.config.mcp_settings"] = MagicMock()

# Now safe to import our exceptions
from tripsage.mcp_abstraction.exceptions import (  # noqa: E402
    MCPAuthenticationError,
    MCPCommunicationProtocolError,
    MCPConfigurationError,
    MCPConnectionError,
    MCPInternalError,
    MCPInvocationError,
    MCPManagerError,
    MCPMethodNotFoundError,
    MCPNotFoundError,
    MCPRateLimitError,
    MCPTimeoutError,
    TripSageMCPError,
)


class TestMCPExceptionHierarchy:
    """Test cases for the MCP exception hierarchy."""

    def test_base_exception(self):
        """Test base TripSageMCPError."""
        error = TripSageMCPError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)

    def test_configuration_error(self):
        """Test MCPConfigurationError."""
        error = MCPConfigurationError("Invalid config")
        assert str(error) == "Invalid config"
        assert isinstance(error, TripSageMCPError)

    def test_connection_error(self):
        """Test MCPConnectionError."""
        error = MCPConnectionError("Connection failed")
        assert str(error) == "Connection failed"
        assert isinstance(error, TripSageMCPError)

    def test_timeout_error(self):
        """Test MCPTimeoutError."""
        error = MCPTimeoutError("Request timed out")
        assert str(error) == "Request timed out"
        assert isinstance(error, TripSageMCPError)

    def test_authentication_error(self):
        """Test MCPAuthenticationError."""
        error = MCPAuthenticationError("Auth failed")
        assert str(error) == "Auth failed"
        assert isinstance(error, TripSageMCPError)

    def test_rate_limit_error(self):
        """Test MCPRateLimitError."""
        error = MCPRateLimitError("Rate limit exceeded")
        assert str(error) == "Rate limit exceeded"
        assert isinstance(error, TripSageMCPError)

    def test_invocation_error(self):
        """Test MCPInvocationError."""
        error = MCPInvocationError("Invocation failed")
        assert str(error) == "Invocation failed"
        assert isinstance(error, TripSageMCPError)

    def test_not_found_error(self):
        """Test MCPNotFoundError."""
        error = MCPNotFoundError("MCP not found")
        assert str(error) == "MCP not found"
        assert isinstance(error, TripSageMCPError)

    def test_manager_error(self):
        """Test MCPManagerError."""
        error = MCPManagerError("Manager error")
        assert str(error) == "Manager error"
        assert isinstance(error, TripSageMCPError)

    def test_method_not_found_error(self):
        """Test MCPMethodNotFoundError."""
        error = MCPMethodNotFoundError("Method not found")
        assert str(error) == "Method not found"
        assert isinstance(error, TripSageMCPError)

    def test_communication_protocol_error(self):
        """Test MCPCommunicationProtocolError."""
        error = MCPCommunicationProtocolError("Protocol error")
        assert str(error) == "Protocol error"
        assert isinstance(error, TripSageMCPError)

    def test_internal_error(self):
        """Test MCPInternalError."""
        error = MCPInternalError("Internal error")
        assert str(error) == "Internal error"
        assert isinstance(error, TripSageMCPError)

    def test_custom_mcp_error_with_context(self):
        """Test custom error with additional context."""
        error = MCPInvocationError(
            "Failed to invoke method", mcp_name="weather", method="get_forecast"
        )

        assert str(error) == "Failed to invoke method"
        assert isinstance(error, TripSageMCPError)

    def test_nested_exception(self):
        """Test exception nesting and cause."""
        original_error = ValueError("Original error")
        error = MCPManagerError("Wrapper error", cause=original_error)

        assert str(error) == "Wrapper error"
        assert isinstance(error, TripSageMCPError)

    def test_exception_with_cause(self):
        """Test exception chaining with cause."""
        original_error = ValueError("Original error")

        # Create exception with cause
        mcp_error = TripSageMCPError("MCP error")
        mcp_error.__cause__ = original_error

        assert str(mcp_error) == "MCP error"
        assert mcp_error.__cause__ == original_error

    def test_exception_hierarchy(self):
        """Test that all specific exceptions inherit from base."""
        exceptions = [
            MCPConfigurationError,
            MCPConnectionError,
            MCPTimeoutError,
            MCPAuthenticationError,
            MCPRateLimitError,
            MCPInvocationError,
            MCPNotFoundError,
            MCPManagerError,
            MCPMethodNotFoundError,
            MCPCommunicationProtocolError,
            MCPInternalError,
        ]

        for exc_class in exceptions:
            instance = exc_class("Test")
            assert isinstance(instance, TripSageMCPError)
            assert isinstance(instance, Exception)
