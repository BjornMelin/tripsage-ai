"""
Standalone tests for MCP exception hierarchy.

This test is in the parent test directory to avoid import issues.
"""

import os
import sys

# Add the tripsage directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Import only the exceptions module directly
from tripsage.mcp_abstraction import exceptions


class TestMCPExceptionHierarchy:
    """Test cases for the MCP exception hierarchy."""

    def test_base_exception(self):
        """Test base TripSageMCPError."""
        error = exceptions.TripSageMCPError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)

    def test_configuration_error(self):
        """Test MCPConfigurationError."""
        error = exceptions.MCPConfigurationError("Invalid config")
        assert str(error) == "Invalid config"
        assert isinstance(error, exceptions.TripSageMCPError)

    def test_connection_error(self):
        """Test MCPConnectionError."""
        error = exceptions.MCPConnectionError("Connection failed")
        assert str(error) == "Connection failed"
        assert isinstance(error, exceptions.TripSageMCPError)

    def test_timeout_error(self):
        """Test MCPTimeoutError."""
        error = exceptions.MCPTimeoutError("Request timed out")
        assert str(error) == "Request timed out"
        assert isinstance(error, exceptions.TripSageMCPError)

    def test_authentication_error(self):
        """Test MCPAuthenticationError."""
        error = exceptions.MCPAuthenticationError("Auth failed")
        assert str(error) == "Auth failed"
        assert isinstance(error, exceptions.TripSageMCPError)

    def test_rate_limit_error(self):
        """Test MCPRateLimitError."""
        error = exceptions.MCPRateLimitError("Rate limit exceeded")
        assert str(error) == "Rate limit exceeded"
        assert isinstance(error, exceptions.TripSageMCPError)

    def test_invocation_error(self):
        """Test MCPInvocationError."""
        error = exceptions.MCPInvocationError("Invocation failed")
        assert str(error) == "Invocation failed"
        assert isinstance(error, exceptions.TripSageMCPError)

    def test_not_found_error(self):
        """Test MCPNotFoundError."""
        error = exceptions.MCPNotFoundError("MCP not found")
        assert str(error) == "MCP not found"
        assert isinstance(error, exceptions.TripSageMCPError)

    def test_manager_error(self):
        """Test MCPManagerError."""
        error = exceptions.MCPManagerError("Manager error")
        assert str(error) == "Manager error"
        assert isinstance(error, exceptions.TripSageMCPError)

    def test_method_not_found_error(self):
        """Test MCPMethodNotFoundError."""
        error = exceptions.MCPMethodNotFoundError("Method not found")
        assert str(error) == "Method not found"
        assert isinstance(error, exceptions.TripSageMCPError)

    def test_communication_protocol_error(self):
        """Test MCPCommunicationProtocolError."""
        error = exceptions.MCPCommunicationProtocolError("Protocol error")
        assert str(error) == "Protocol error"
        assert isinstance(error, exceptions.TripSageMCPError)

    def test_internal_error(self):
        """Test MCPInternalError."""
        error = exceptions.MCPInternalError("Internal error")
        assert str(error) == "Internal error"
        assert isinstance(error, exceptions.TripSageMCPError)

    def test_exception_hierarchy(self):
        """Test that all specific exceptions inherit from base."""
        exception_classes = [
            exceptions.MCPConfigurationError,
            exceptions.MCPConnectionError,
            exceptions.MCPTimeoutError,
            exceptions.MCPAuthenticationError,
            exceptions.MCPRateLimitError,
            exceptions.MCPInvocationError,
            exceptions.MCPNotFoundError,
            exceptions.MCPManagerError,
            exceptions.MCPMethodNotFoundError,
            exceptions.MCPCommunicationProtocolError,
            exceptions.MCPInternalError,
        ]

        for exc_class in exception_classes:
            instance = exc_class("Test")
            assert isinstance(instance, exceptions.TripSageMCPError)
            assert isinstance(instance, Exception)
