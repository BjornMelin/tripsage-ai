"""
Comprehensive tests for exception handlers in api/main.py.

This module tests all exception handlers implemented in the main FastAPI application,
ensuring proper error formatting, status codes, and response structures.
"""

import asyncio
from unittest.mock import Mock, patch

import pytest
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient

from api.main import create_application
from tripsage_core.exceptions.exceptions import (
    CoreAgentError,
    CoreAuthenticationError,
    CoreAuthorizationError,
    CoreDatabaseError,
    CoreExternalAPIError,
    CoreKeyValidationError,
    CoreMCPError,
    CoreRateLimitError,
    CoreResourceNotFoundError,
    CoreServiceError,
    CoreTripSageError,
    CoreValidationError,
    ErrorDetails,
)


class TestExceptionHandlers:
    """Test class for all exception handlers."""

    @pytest.fixture
    def app(self):
        """Create a test FastAPI application."""
        return create_application()

    @pytest.fixture
    def client(self, app):
        """Create a test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_request(self):
        """Create a mock request object."""
        request = Mock(spec=Request)
        request.url = Mock()
        request.url.path = "/test"
        request.method = "GET"
        return request

    def test_authentication_error_handler(self, app, mock_request):
        """Test authentication error handler."""
        CoreAuthenticationError(
            message="Invalid credentials",
            code="INVALID_CREDENTIALS",
            details=ErrorDetails(user_id="user123"),
        )

        # Get the handler from the app
        handler = None
        for exception_handler in app.exception_handlers.values():
            if (
                hasattr(exception_handler, "__name__")
                and "authentication" in exception_handler.__name__
            ):
                handler = exception_handler
                break

        assert handler is not None, "Authentication error handler not found"

    def test_authorization_error_handler(self, app, mock_request):
        """Test authorization error handler."""
        CoreAuthorizationError(
            message="Access denied to resource",
            code="ACCESS_DENIED",
            details=ErrorDetails(user_id="user123", resource_id="resource456"),
        )

        # Test that the handler exists
        assert CoreAuthorizationError in app.exception_handlers

    def test_resource_not_found_error_handler(self, app, mock_request):
        """Test resource not found error handler."""
        CoreResourceNotFoundError(
            message="Trip not found",
            code="TRIP_NOT_FOUND",
            details=ErrorDetails(resource_id="trip123"),
        )

        # Test that the handler exists
        assert CoreResourceNotFoundError in app.exception_handlers

    def test_validation_error_handler(self, app, mock_request):
        """Test core validation error handler."""
        CoreValidationError(
            message="Invalid email format",
            code="INVALID_EMAIL",
            details=ErrorDetails(additional_context={"field": "email"}),
        )

        # Test that the handler exists
        assert CoreValidationError in app.exception_handlers

    def test_service_error_handler(self, app, mock_request):
        """Test service error handler."""
        CoreServiceError(
            message="Database connection failed",
            code="DB_CONNECTION_ERROR",
            details=ErrorDetails(service="database"),
        )

        # Test that the handler exists
        assert CoreServiceError in app.exception_handlers

    def test_rate_limit_error_handler(self, app, mock_request):
        """Test rate limit error handler."""
        CoreRateLimitError(
            message="Too many requests",
            code="RATE_LIMIT_EXCEEDED",
            details=ErrorDetails(additional_context={"retry_after": 60}),
        )

        # Test that the handler exists
        assert CoreRateLimitError in app.exception_handlers

    def test_key_validation_error_handler(self, app, mock_request):
        """Test API key validation error handler."""
        CoreKeyValidationError(
            message="Invalid OpenAI API key",
            code="INVALID_OPENAI_KEY",
            details=ErrorDetails(service="openai"),
        )

        # Test that the handler exists
        assert CoreKeyValidationError in app.exception_handlers

    def test_database_error_handler(self, app, mock_request):
        """Test database error handler."""
        CoreDatabaseError(
            message="Connection timeout",
            code="DB_TIMEOUT",
            details=ErrorDetails(
                operation="SELECT", additional_context={"table": "users"}
            ),
        )

        # Test that the handler exists
        assert CoreDatabaseError in app.exception_handlers

    def test_external_api_error_handler(self, app, mock_request):
        """Test external API error handler."""
        CoreExternalAPIError(
            message="Duffel API error",
            code="DUFFEL_API_ERROR",
            details=ErrorDetails(service="duffel"),
        )

        # Test that the handler exists
        assert CoreExternalAPIError in app.exception_handlers

    def test_mcp_error_handler(self, app, mock_request):
        """Test MCP error handler."""
        CoreMCPError(
            message="MCP server unavailable",
            code="MCP_SERVER_ERROR",
            details=ErrorDetails(service="flights_mcp"),
        )

        # Test that the handler exists
        assert CoreMCPError in app.exception_handlers

    def test_agent_error_handler(self, app, mock_request):
        """Test agent error handler."""
        CoreAgentError(
            message="Agent execution failed",
            code="AGENT_EXECUTION_ERROR",
            details=ErrorDetails(service="travel_agent", operation="plan_trip"),
        )

        # Test that the handler exists
        assert CoreAgentError in app.exception_handlers

    def test_core_tripsage_error_handler(self, app, mock_request):
        """Test general core TripSage error handler."""
        CoreTripSageError(
            message="Generic error",
            code="GENERIC_ERROR",
            status_code=500,
        )

        # Test that the handler exists
        assert CoreTripSageError in app.exception_handlers

    def test_request_validation_error_handler(self, app):
        """Test FastAPI request validation error handler."""
        # Test that the handler exists
        assert RequestValidationError in app.exception_handlers

    def test_generic_exception_handler(self, app):
        """Test generic exception handler."""
        # Test that the handler exists
        assert Exception in app.exception_handlers


class TestExceptionHandlersIntegration:
    """Integration tests for exception handlers with actual HTTP requests."""

    @pytest.fixture
    def app(self):
        """Create a test FastAPI application with test routes."""
        app = create_application()

        # Add test routes that raise specific exceptions
        @app.get("/test/auth-error")
        async def test_auth_error():
            raise CoreAuthenticationError("Test authentication error")

        @app.get("/test/auth-error-with-details")
        async def test_auth_error_with_details():
            raise CoreAuthenticationError(
                "Invalid token",
                details=ErrorDetails(user_id="user123"),
            )

        @app.get("/test/authorization-error")
        async def test_authorization_error():
            raise CoreAuthorizationError("Test authorization error")

        @app.get("/test/not-found")
        async def test_not_found():
            raise CoreResourceNotFoundError("Test resource not found")

        @app.get("/test/validation-error")
        async def test_validation_error():
            raise CoreValidationError("Test validation error")

        @app.get("/test/service-error")
        async def test_service_error():
            raise CoreServiceError("Test service error")

        @app.get("/test/rate-limit")
        async def test_rate_limit():
            raise CoreRateLimitError(
                "Rate limit exceeded",
                details=ErrorDetails(additional_context={"retry_after": 60}),
            )

        @app.get("/test/key-validation")
        async def test_key_validation():
            raise CoreKeyValidationError("Invalid API key")

        @app.get("/test/database-error")
        async def test_database_error():
            raise CoreDatabaseError("Database connection failed")

        @app.get("/test/external-api-error")
        async def test_external_api_error():
            raise CoreExternalAPIError("External API failed")

        @app.get("/test/mcp-error")
        async def test_mcp_error():
            raise CoreMCPError("MCP server error")

        @app.get("/test/agent-error")
        async def test_agent_error():
            raise CoreAgentError("Agent execution failed")

        @app.get("/test/core-error")
        async def test_core_error():
            raise CoreTripSageError("Generic core error")

        @app.get("/test/generic-error")
        async def test_generic_error():
            raise ValueError("Generic Python error")

        @app.post("/test/validation-error")
        async def test_pydantic_validation_error(data: dict):
            # This will trigger RequestValidationError
            pass

        return app

    @pytest.fixture
    def client(self, app):
        """Create a test client."""
        return TestClient(app)

    def test_authentication_error_response(self, client):
        """Test authentication error response format."""
        response = client.get("/test/auth-error")

        assert response.status_code == 401
        data = response.json()
        assert data["error"] == "AUTHENTICATION_ERROR"
        assert data["message"] == "Test authentication error"
        assert "details" in data

    def test_authentication_error_with_details_response(self, client):
        """Test authentication error response with details."""
        response = client.get("/test/auth-error-with-details")

        assert response.status_code == 401
        data = response.json()
        assert data["error"] == "AUTHENTICATION_ERROR"
        assert data["message"] == "Invalid token"
        assert data["details"]["user_id"] == "user123"

    def test_authorization_error_response(self, client):
        """Test authorization error response format."""
        response = client.get("/test/authorization-error")

        assert response.status_code == 403
        data = response.json()
        assert data["error"] == "AUTHORIZATION_ERROR"
        assert data["message"] == "Test authorization error"

    def test_not_found_error_response(self, client):
        """Test not found error response format."""
        response = client.get("/test/not-found")

        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "RESOURCE_NOT_FOUND"
        assert data["message"] == "Test resource not found"

    def test_validation_error_response(self, client):
        """Test validation error response format."""
        response = client.get("/test/validation-error")

        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "VALIDATION_ERROR"
        assert data["message"] == "Test validation error"

    def test_service_error_response(self, client):
        """Test service error response format."""
        response = client.get("/test/service-error")

        assert response.status_code == 502
        data = response.json()
        assert data["error"] == "SERVICE_ERROR"
        assert data["message"] == "Test service error"

    def test_rate_limit_error_response(self, client):
        """Test rate limit error response format."""
        response = client.get("/test/rate-limit")

        assert response.status_code == 429
        assert "Retry-After" in response.headers
        assert response.headers["Retry-After"] == "60"

        data = response.json()
        assert data["error"] == "RATE_LIMIT_EXCEEDED"
        assert data["message"] == "Rate limit exceeded"

    def test_key_validation_error_response(self, client):
        """Test key validation error response format."""
        response = client.get("/test/key-validation")

        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "INVALID_API_KEY"
        assert data["message"] == "Invalid API key"

    def test_database_error_response(self, client):
        """Test database error response format."""
        response = client.get("/test/database-error")

        assert response.status_code == 500
        data = response.json()
        assert data["error"] == "DATABASE_ERROR"
        assert "database error occurred" in data["message"].lower()

    def test_external_api_error_response(self, client):
        """Test external API error response format."""
        response = client.get("/test/external-api-error")

        assert response.status_code == 502
        data = response.json()
        assert data["error"] == "EXTERNAL_API_ERROR"
        assert "external service" in data["message"].lower()

    def test_mcp_error_response(self, client):
        """Test MCP error response format."""
        response = client.get("/test/mcp-error")

        assert response.status_code == 502
        data = response.json()
        assert data["error"] == "MCP_ERROR"
        assert "service component" in data["message"].lower()

    def test_agent_error_response(self, client):
        """Test agent error response format."""
        response = client.get("/test/agent-error")

        assert response.status_code == 502
        data = response.json()
        assert data["error"] == "AGENT_ERROR"
        assert "AI agent" in data["message"]

    def test_core_error_response(self, client):
        """Test core TripSage error response format."""
        response = client.get("/test/core-error")

        assert response.status_code == 500
        data = response.json()
        assert data["error"] == "INTERNAL_ERROR"
        assert data["message"] == "Generic core error"

    def test_generic_error_response(self, client):
        """Test generic exception response format."""
        response = client.get("/test/generic-error")

        assert response.status_code == 500
        data = response.json()
        assert data["error"] == "SYSTEM_ERROR"
        # In debug mode (default for tests), should show the actual error
        assert "Generic Python error" in data["message"]

    @patch("api.core.config.settings.debug", False)
    def test_generic_error_response_production(self, client):
        """Test generic exception response in production mode."""
        response = client.get("/test/generic-error")

        assert response.status_code == 500
        data = response.json()
        assert data["error"] == "INTERNAL_ERROR"
        assert "unexpected error occurred" in data["message"].lower()
        assert data["details"] is None

    def test_request_validation_error_response(self, client):
        """Test FastAPI request validation error response."""
        # Send invalid JSON to trigger validation error
        response = client.post("/test/validation-error", json="invalid")

        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "VALIDATION_ERROR"
        assert "validation failed" in data["message"].lower()
        assert "details" in data
        assert "errors" in data["details"]
        assert data["details"]["error_count"] > 0

    def test_health_endpoint_still_works(self, client):
        """Test that health endpoint works normally."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


class TestExceptionHandlerHelpers:
    """Test helper functions in exception handlers."""

    @pytest.fixture
    def app(self):
        """Create a test FastAPI application."""
        return create_application()

    def test_format_details_helper_with_details(self, app):
        """Test _format_details helper with details object."""
        # We need to access the helper function from within the handler
        # This tests the logic by testing the actual behavior
        details = ErrorDetails(user_id="user123", service="test")

        # Test that details are properly formatted by checking a response
        test_app = create_application()

        @test_app.get("/test/details")
        async def test_details():
            raise CoreAuthenticationError(
                "Test error",
                details=details,
            )

        client = TestClient(test_app)
        response = client.get("/test/details")

        assert response.status_code == 401
        data = response.json()
        assert data["details"]["user_id"] == "user123"
        assert data["details"]["service"] == "test"

    def test_format_details_helper_no_details(self, app):
        """Test _format_details helper with no details."""
        test_app = create_application()

        @test_app.get("/test/no-details")
        async def test_no_details():
            raise CoreAuthenticationError("Test error")

        client = TestClient(test_app)
        response = client.get("/test/no-details")

        assert response.status_code == 401
        data = response.json()
        # Details should be None when no details provided
        assert data["details"] == {} or data["details"] is None

    @patch("api.core.config.settings.debug", False)
    def test_format_details_helper_debug_disabled(self, app):
        """Test _format_details helper with debug disabled."""
        test_app = create_application()

        @test_app.get("/test/debug-disabled")
        async def test_debug_disabled():
            raise CoreDatabaseError(
                "Database error",
                details=ErrorDetails(operation="SELECT"),
            )

        client = TestClient(test_app)
        response = client.get("/test/debug-disabled")

        assert response.status_code == 500
        data = response.json()
        # In production mode with debug disabled, sensitive details should be hidden
        assert data["details"] is None


@pytest.mark.asyncio
class TestAsyncExceptionHandlers:
    """Test async aspects of exception handlers."""

    async def test_async_handler_execution(self):
        """Test that exception handlers work with async endpoints."""
        app = create_application()

        @app.get("/test/async-error")
        async def async_error_endpoint():
            await asyncio.sleep(0.001)  # Small async operation
            raise CoreAuthenticationError("Async auth error")

        client = TestClient(app)
        response = client.get("/test/async-error")

        assert response.status_code == 401
        data = response.json()
        assert data["error"] == "AUTHENTICATION_ERROR"
        assert data["message"] == "Async auth error"


class TestExceptionHandlerEdgeCases:
    """Test edge cases and error scenarios."""

    @pytest.fixture
    def app(self):
        """Create a test FastAPI application."""
        return create_application()

    @pytest.fixture
    def client(self, app):
        """Create a test client."""
        return TestClient(app)

    def test_exception_with_none_details(self, client):
        """Test exception with explicitly None details."""
        app = create_application()

        @app.get("/test/none-details")
        async def test_none_details():
            raise CoreAuthenticationError("Error", details=None)

        client = TestClient(app)
        response = client.get("/test/none-details")

        assert response.status_code == 401
        data = response.json()
        assert data["details"] is None or data["details"] == {}

    def test_exception_with_empty_additional_context(self, client):
        """Test exception with empty additional context."""
        app = create_application()

        @app.get("/test/empty-context")
        async def test_empty_context():
            details = ErrorDetails(additional_context={})
            raise CoreRateLimitError("Rate limit", details=details)

        client = TestClient(app)
        response = client.get("/test/empty-context")

        assert response.status_code == 429
        # Should not have Retry-After header since retry_after not in context
        assert "Retry-After" not in response.headers

    def test_malformed_validation_errors(self, client):
        """Test handling of malformed validation errors."""
        app = create_application()

        @app.post("/test/malformed")
        async def test_malformed(item: dict):
            pass

        client = TestClient(app)
        # Send completely invalid data
        response = client.post("/test/malformed", data="not json")

        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "VALIDATION_ERROR"
        assert "validation failed" in data["message"].lower()

    def test_large_error_details(self, client):
        """Test handling of large error details."""
        app = create_application()

        @app.get("/test/large-details")
        async def test_large_details():
            large_context = {f"key_{i}": f"value_{i}" * 100 for i in range(50)}
            details = ErrorDetails(additional_context=large_context)
            raise CoreServiceError("Large details", details=details)

        client = TestClient(app)
        response = client.get("/test/large-details")

        assert response.status_code == 502
        data = response.json()
        assert data["error"] == "SERVICE_ERROR"
        # Should still handle large details without crashing
        assert "details" in data
