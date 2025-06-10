"""
Clean, consolidated tests for error_handling_utils module.

Tests real-world error handling scenarios with proper mocking and
actionable assertions that verify actual TripSage functionality.
"""

import logging
from unittest.mock import MagicMock, patch

import pytest

from tripsage_core.exceptions import (
    CoreDatabaseError,
    CoreExternalAPIError,
    CoreMCPError,
    CoreTripSageError,
    CoreValidationError,
)
from tripsage_core.utils.error_handling_utils import (
    TripSageErrorContext,
    create_api_error,
    create_database_error,
    create_mcp_error,
    create_validation_error,
    log_exception,
    safe_execute_with_logging,
    with_error_handling_and_logging,
)


class TestLogException:
    """Test exception logging with real TripSage error types."""

    @patch('tripsage_core.utils.error_handling_utils.get_logger')
    def test_logs_mcp_error_correctly(self, mock_get_logger):
        """Test MCP error logging includes server and tool details."""
        mock_logger = MagicMock(spec=logging.Logger)
        mock_get_logger.return_value = mock_logger
        
        error = create_mcp_error(
            "Tool failed", 
            server="airbnb", 
            tool="search_properties", 
            params={"location": "NYC"}
        )
        
        log_exception(error, "test_logger")
        
        # Verify error-level logging with MCP details
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args[0]
        assert "MCP Error" in call_args[0]
        assert "airbnb" in call_args[2]
        assert "search_properties" in call_args[3]

    @patch('tripsage_core.utils.error_handling_utils.get_logger')
    def test_logs_api_error_correctly(self, mock_get_logger):
        """Test API error logging includes service and status details."""
        mock_logger = MagicMock(spec=logging.Logger)
        mock_get_logger.return_value = mock_logger
        
        error = create_api_error(
            "Rate limit exceeded", 
            service="duffel", 
            status_code=429,
            response={"error": "too_many_requests"}
        )
        
        log_exception(error, "test_logger")
        
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args[0]
        assert "API Error" in call_args[0]
        assert "duffel" in call_args[2]
        assert "429" in str(call_args[3])

    @patch('tripsage_core.utils.error_handling_utils.get_logger')
    def test_logs_validation_error_as_warning(self, mock_get_logger):
        """Test validation errors use warning level."""
        mock_logger = MagicMock(spec=logging.Logger)
        mock_get_logger.return_value = mock_logger
        
        error = create_validation_error(
            "Invalid date format", 
            field="departure_date", 
            value="invalid-date"
        )
        
        log_exception(error, "test_logger")
        
        # Validation errors should use warning level
        mock_logger.warning.assert_called_once()
        mock_logger.error.assert_not_called()

    @patch('tripsage_core.utils.error_handling_utils.get_logger')
    def test_logs_standard_exception_as_error(self, mock_get_logger):
        """Test standard exceptions use error level."""
        mock_logger = MagicMock(spec=logging.Logger)
        mock_get_logger.return_value = mock_logger
        
        error = ValueError("Something went wrong")
        
        log_exception(error, "test_logger")
        
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args[0]
        assert "System error" in call_args[0]
        assert "ValueError" in call_args[1]


class TestErrorFactories:
    """Test error creation factory functions."""

    def test_create_mcp_error_formats_correctly(self):
        """Test MCP error creation with TripSage formatting."""
        error = create_mcp_error(
            "Connection failed",
            server="google_maps",
            tool="geocode",
            category="connection"
        )
        
        assert isinstance(error, CoreMCPError)
        assert error.message == "Connection failed"
        assert error.details.service == "google_maps"
        assert error.details.additional_context["tool"] == "geocode"
        assert error.code == "MCP_CONNECTION_ERROR"

    def test_create_api_error_formats_correctly(self):
        """Test API error creation with service details."""
        error = create_api_error(
            "Authentication failed",
            service="openai",
            status_code=401
        )
        
        assert isinstance(error, CoreExternalAPIError)
        assert error.message == "Authentication failed"
        assert error.details.service == "openai"
        assert error.details.additional_context["api_status_code"] == 401
        assert error.code == "OPENAI_API_ERROR"

    def test_create_database_error_formats_correctly(self):
        """Test database error creation."""
        error = create_database_error(
            "Connection timeout",
            operation="select",
            table="trips"
        )
        
        assert isinstance(error, CoreDatabaseError)
        assert error.message == "Connection timeout"
        assert error.details.operation == "select"
        assert error.details.additional_context["table"] == "trips"


class TestSafeExecuteWithLogging:
    """Test safe execution with logging wrapper."""

    def test_executes_function_successfully(self):
        """Test successful function execution."""
        def mock_function(x, y):
            return x + y
        
        result = safe_execute_with_logging(mock_function, 2, 3)
        assert result == 5

    def test_returns_fallback_on_error(self):
        """Test fallback value returned on error."""
        def failing_function():
            raise ValueError("Test error")
        
        result = safe_execute_with_logging(failing_function, fallback="fallback")
        assert result == "fallback"

    def test_handles_keyword_arguments(self):
        """Test function execution with keyword arguments."""
        def mock_function(x, y=10):
            return x * y
        
        result = safe_execute_with_logging(mock_function, 3, y=4)
        assert result == 12


class TestErrorHandlingDecorator:
    """Test error handling decorator."""

    def test_decorator_handles_errors(self):
        """Test decorator catches and handles errors."""
        @with_error_handling_and_logging(fallback="error_occurred")
        def failing_function():
            raise RuntimeError("Test error")
        
        result = failing_function()
        assert result == "error_occurred"

    def test_decorator_passes_through_success(self):
        """Test decorator allows successful execution."""
        @with_error_handling_and_logging()
        def successful_function():
            return "success"
        
        result = successful_function()
        assert result == "success"


class TestTripSageErrorContext:
    """Test enhanced error context manager."""

    @pytest.fixture
    def mock_logger(self):
        logger = MagicMock(spec=logging.Logger)
        logger.name = "test_logger"
        return logger

    def test_context_logs_operation_start_and_end(self, mock_logger):
        """Test context manager logs operation lifecycle."""
        with TripSageErrorContext(
            "search_flights", 
            service="duffel", 
            user_id="user123",
            logger_instance=mock_logger
        ):
            pass  # Successful operation
        
        # Should log start and completion
        assert mock_logger.debug.call_count == 2
        start_call = mock_logger.debug.call_args_list[0]
        end_call = mock_logger.debug.call_args_list[1]
        
        assert "Starting operation" in start_call[0][0]
        assert "Completed operation" in end_call[0][0]

    def test_context_enhances_tripsage_errors(self, mock_logger):
        """Test context manager enhances TripSage errors with metadata."""
        validation_error = create_validation_error(
            "Invalid input", 
            field="destination"
        )
        
        with pytest.raises(CoreValidationError) as exc_info:
            with TripSageErrorContext(
                "validate_search",
                service="search_service",
                user_id="user123",
                logger_instance=mock_logger
            ):
                raise validation_error
        
        # Error should be enhanced with context
        enhanced_error = exc_info.value
        assert enhanced_error.details.operation == "validate_search"
        assert enhanced_error.details.service == "search_service"
        assert enhanced_error.details.user_id == "user123"

    def test_context_handles_standard_exceptions(self, mock_logger):
        """Test context manager handles non-TripSage exceptions."""
        with pytest.raises(ValueError):
            with TripSageErrorContext(
                "process_data",
                logger_instance=mock_logger
            ):
                raise ValueError("Standard error")
        
        # Should still log the error
        mock_logger.debug.assert_called()


class TestIntegrationScenarios:
    """Test real-world integration scenarios."""

    @patch('tripsage_core.utils.error_handling_utils.logger')
    def test_flight_search_error_workflow(self, mock_logger):
        """Test realistic flight search error handling."""
        # Simulate Duffel API failure
        api_error = create_api_error(
            "Rate limit exceeded",
            service="duffel",
            status_code=429,
            response={"retry_after": 60}
        )
        
        with TripSageErrorContext(
            "search_flights",
            service="flight_service", 
            user_id="user123"
        ):
            log_exception(api_error)
        
        # Verify comprehensive error logging
        mock_logger.error.assert_called_once()
        
    def test_mcp_integration_error_handling(self):
        """Test MCP integration error scenarios."""
        @with_error_handling_and_logging(fallback=[])
        def search_accommodations():
            # Simulate Airbnb MCP failure
            raise create_mcp_error(
                "Server unavailable",
                server="airbnb",
                tool="search_properties",
                category="connectivity"
            )
        
        result = search_accommodations()
        assert result == []  # Fallback value