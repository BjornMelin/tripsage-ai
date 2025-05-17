"""
Direct tests for MCP exception hierarchy.

This module directly imports only the exceptions module without going through init.
"""

# Import exceptions directly
from tripsage.mcp_abstraction.exceptions import (
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
