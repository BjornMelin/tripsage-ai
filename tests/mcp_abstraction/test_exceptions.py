"""
Tests for MCP exception hierarchy.

This module tests the custom exception classes used throughout
the MCP abstraction layer.
"""

import pytest

from tripsage.mcp_abstraction.exceptions import (
    MCPAuthenticationError,
    MCPConfigurationError,
    MCPConnectionError,
    MCPExecutionError,
    MCPNotFoundError,
    MCPRateLimitError,
    MCPTimeoutError,
    MCPValidationError,
    TripSageMCPError,
)


class TestMCPExceptions:
    """Tests for MCP exception classes."""

    def test_base_exception(self):
        """Test the base TripSageMCPError."""
        error = TripSageMCPError("Base error message")

        assert str(error) == "Base error message"
        assert isinstance(error, Exception)

    def test_configuration_error(self):
        """Test MCPConfigurationError."""
        error = MCPConfigurationError("Invalid configuration")

        assert str(error) == "Invalid configuration"
        assert isinstance(error, TripSageMCPError)
        assert isinstance(error, Exception)

    def test_connection_error(self):
        """Test MCPConnectionError."""
        error = MCPConnectionError("Failed to connect")

        assert str(error) == "Failed to connect"
        assert isinstance(error, TripSageMCPError)

    def test_timeout_error(self):
        """Test MCPTimeoutError."""
        error = MCPTimeoutError("Request timed out")

        assert str(error) == "Request timed out"
        assert isinstance(error, TripSageMCPError)

    def test_authentication_error(self):
        """Test MCPAuthenticationError."""
        error = MCPAuthenticationError("Invalid credentials")

        assert str(error) == "Invalid credentials"
        assert isinstance(error, TripSageMCPError)

    def test_rate_limit_error(self):
        """Test MCPRateLimitError."""
        error = MCPRateLimitError("Rate limit exceeded")

        assert str(error) == "Rate limit exceeded"
        assert isinstance(error, TripSageMCPError)

    def test_not_found_error(self):
        """Test MCPNotFoundError."""
        error = MCPNotFoundError("Resource not found")

        assert str(error) == "Resource not found"
        assert isinstance(error, TripSageMCPError)

    def test_validation_error(self):
        """Test MCPValidationError."""
        error = MCPValidationError("Invalid input data")

        assert str(error) == "Invalid input data"
        assert isinstance(error, TripSageMCPError)

    def test_execution_error(self):
        """Test MCPExecutionError."""
        error = MCPExecutionError("Execution failed")

        assert str(error) == "Execution failed"
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
            MCPNotFoundError,
            MCPValidationError,
            MCPExecutionError,
        ]

        for exc_class in exceptions:
            error = exc_class("Test message")
            assert isinstance(error, TripSageMCPError)
            assert isinstance(error, Exception)

    def test_exception_context(self):
        """Test exceptions with additional context."""
        error = MCPConnectionError("Failed to connect to service")
        error.service = "weather"
        error.method = "get_current_weather"
        error.attempt = 3

        assert hasattr(error, "service")
        assert error.service == "weather"
        assert error.method == "get_current_weather"
        assert error.attempt == 3

    def test_exception_repr(self):
        """Test exception string representation."""
        error = TripSageMCPError("Test error")

        assert repr(error) == "TripSageMCPError('Test error')"

    def test_raise_and_catch_hierarchy(self):
        """Test raising and catching exceptions in hierarchy."""

        # Test catching specific exception
        with pytest.raises(MCPTimeoutError):
            raise MCPTimeoutError("Timeout")

        # Test catching base exception
        with pytest.raises(TripSageMCPError):
            raise MCPTimeoutError("Timeout")

        # Test that it's a standard Exception subclass
        assert issubclass(MCPTimeoutError, Exception)

    def test_exception_error_codes(self):
        """Test that exceptions can have error codes."""
        error = MCPAuthenticationError("Invalid API key")
        error.code = "AUTH_001"
        error.status_code = 401

        assert error.code == "AUTH_001"
        assert error.status_code == 401

    def test_exception_retry_info(self):
        """Test that exceptions can have retry information."""
        error = MCPRateLimitError("Rate limit exceeded")
        error.retry_after = 60  # seconds
        error.retry_count = 3

        assert error.retry_after == 60
        assert error.retry_count == 3
