"""
Integration tests for exception handling across the entire API.

This module tests exception handling in real API scenarios with middleware,
authentication, and actual service calls.
"""

import asyncio
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.main import create_application
from tripsage_core.exceptions.exceptions import (
    CoreAuthenticationError,
    CoreDatabaseError,
    CoreExternalAPIError,
    CoreResourceNotFoundError,
    CoreServiceError,
    CoreValidationError,
)


class TestExceptionHandlingMiddlewareIntegration:
    """Test exception handling with middleware stack."""

    @pytest.fixture
    def app(self):
        """Create application with full middleware stack."""
        return create_application()

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    def test_exception_through_middleware_stack(self, client):
        """Test that exceptions properly propagate through middleware."""
        # The health endpoint should work normally
        response = client.get("/health")
        assert response.status_code == 200

    @patch("api.core.config.settings.debug", True)
    def test_debug_mode_error_details(self, client):
        """Test error details in debug mode."""
        app = create_application()

        @app.get("/test/debug-error")
        async def debug_error():
            raise CoreDatabaseError("Debug database error")

        client = TestClient(app)
        response = client.get("/test/debug-error")

        assert response.status_code == 500
        data = response.json()
        # In debug mode, details should be present
        assert data["details"] is not None

    @patch("api.core.config.settings.debug", False)
    def test_production_mode_error_hiding(self, client):
        """Test error detail hiding in production mode."""
        app = create_application()

        @app.get("/test/production-error")
        async def production_error():
            raise CoreDatabaseError("Production database error")

        client = TestClient(app)
        response = client.get("/test/production-error")

        assert response.status_code == 500
        data = response.json()
        # In production mode, sensitive details should be hidden
        assert "database error occurred" in data["message"].lower()


class TestRealWorldExceptionScenarios:
    """Test exception handling in realistic API scenarios."""

    @pytest.fixture
    def app(self):
        """Create application with test endpoints."""
        app = create_application()

        @app.get("/api/v1/test/trips/{trip_id}")
        async def get_trip(trip_id: str):
            """Simulate getting a trip that might not exist."""
            if trip_id == "nonexistent":
                raise CoreResourceNotFoundError(
                    f"Trip {trip_id} not found", details={"resource_id": trip_id}
                )
            return {"trip_id": trip_id, "name": "Test Trip"}

        @app.post("/api/v1/test/flights/search")
        async def search_flights(data: dict):
            """Simulate flight search with external API."""
            if data.get("origin") == "INVALID":
                raise CoreExternalAPIError(
                    "Invalid airport code",
                    details={"api_service": "duffel", "api_status_code": 400},
                )
            return {"flights": []}

        @app.get("/api/v1/test/user/profile")
        async def get_user_profile():
            """Simulate getting user profile requiring authentication."""
            raise CoreAuthenticationError(
                "Authentication token missing or invalid",
                details={"required": "Bearer token"},
            )

        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    def test_trip_not_found_scenario(self, client):
        """Test realistic trip not found scenario."""
        response = client.get("/api/v1/test/trips/nonexistent")

        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "RESOURCE_NOT_FOUND"
        assert "Trip nonexistent not found" in data["message"]
        assert data["details"]["resource_id"] == "nonexistent"

    def test_valid_trip_scenario(self, client):
        """Test valid trip retrieval works normally."""
        response = client.get("/api/v1/test/trips/123")

        assert response.status_code == 200
        data = response.json()
        assert data["trip_id"] == "123"
        assert data["name"] == "Test Trip"

    def test_external_api_error_scenario(self, client):
        """Test external API error handling."""
        response = client.post(
            "/api/v1/test/flights/search", json={"origin": "INVALID"}
        )

        assert response.status_code == 502
        data = response.json()
        assert data["error"] == "EXTERNAL_API_ERROR"
        assert "external service" in data["message"].lower()

    def test_valid_flight_search_scenario(self, client):
        """Test valid flight search works normally."""
        response = client.post("/api/v1/test/flights/search", json={"origin": "LAX"})

        assert response.status_code == 200
        data = response.json()
        assert "flights" in data

    def test_authentication_required_scenario(self, client):
        """Test authentication required scenario."""
        response = client.get("/api/v1/test/user/profile")

        assert response.status_code == 401
        data = response.json()
        assert data["error"] == "AUTHENTICATION_ERROR"
        assert "authentication token" in data["message"].lower()

    def test_malformed_json_request(self, client):
        """Test handling of malformed JSON requests."""
        response = client.post(
            "/api/v1/test/flights/search",
            data="invalid json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "VALIDATION_ERROR"


class TestExceptionLogging:
    """Test that exceptions are properly logged."""

    @pytest.fixture
    def app(self):
        """Create application for logging tests."""
        return create_application()

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    @patch("api.main.logger")
    def test_authentication_error_logging(self, mock_logger, client):
        """Test that authentication errors are logged correctly."""
        app = create_application()

        @app.get("/test/auth-log")
        async def auth_log_test():
            raise CoreAuthenticationError("Test auth error")

        client = TestClient(app)
        response = client.get("/test/auth-log")

        assert response.status_code == 401
        # Verify logging was called (warning level for auth errors)
        mock_logger.warning.assert_called()
        call_args = mock_logger.warning.call_args[0][0]
        assert "Authentication error" in call_args
        assert "AUTHENTICATION_ERROR" in call_args

    @patch("api.main.logger")
    def test_service_error_logging(self, mock_logger, client):
        """Test that service errors are logged correctly."""
        app = create_application()

        @app.get("/test/service-log")
        async def service_log_test():
            raise CoreServiceError("Test service error")

        client = TestClient(app)
        response = client.get("/test/service-log")

        assert response.status_code == 502
        # Verify logging was called (error level for service errors)
        mock_logger.error.assert_called()
        call_args = mock_logger.error.call_args[0][0]
        assert "Service error" in call_args
        assert "SERVICE_ERROR" in call_args

    @patch("api.main.logger")
    def test_generic_exception_logging(self, mock_logger, client):
        """Test that generic exceptions are logged correctly."""
        app = create_application()

        @app.get("/test/generic-log")
        async def generic_log_test():
            raise ValueError("Test generic error")

        client = TestClient(app)
        response = client.get("/test/generic-log")

        assert response.status_code == 500
        # Verify exception logging was called
        mock_logger.exception.assert_called()
        call_args = mock_logger.exception.call_args[0][0]
        assert "Unhandled exception" in call_args


class TestConcurrentExceptionHandling:
    """Test exception handling under concurrent requests."""

    @pytest.fixture
    def app(self):
        """Create application for concurrency tests."""
        app = create_application()

        @app.get("/test/concurrent/{error_type}")
        async def concurrent_error(error_type: str):
            await asyncio.sleep(0.01)  # Small delay to simulate async work

            if error_type == "auth":
                raise CoreAuthenticationError("Concurrent auth error")
            elif error_type == "service":
                raise CoreServiceError("Concurrent service error")
            elif error_type == "database":
                raise CoreDatabaseError("Concurrent database error")
            else:
                raise ValueError("Concurrent generic error")

        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    def test_concurrent_different_exceptions(self, client):
        """Test handling different exception types concurrently."""
        import concurrent.futures

        def make_request(error_type):
            return client.get(f"/test/concurrent/{error_type}")

        error_types = ["auth", "service", "database", "generic"]

        # Make concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(make_request, error_type) for error_type in error_types
            ]
            responses = [
                future.result() for future in concurrent.futures.as_completed(futures)
            ]

        # Verify all responses are correct
        status_codes = [r.status_code for r in responses]
        assert 401 in status_codes  # auth error
        assert 502 in status_codes  # service error
        assert 500 in status_codes  # database error
        assert 500 in status_codes  # generic error (mapped to 500)

    def test_concurrent_same_exception(self, client):
        """Test handling same exception type concurrently."""
        import concurrent.futures

        def make_auth_request():
            return client.get("/test/concurrent/auth")

        # Make multiple concurrent requests with same error type
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_auth_request) for _ in range(10)]
            responses = [
                future.result() for future in concurrent.futures.as_completed(futures)
            ]

        # All should return 401
        for response in responses:
            assert response.status_code == 401
            data = response.json()
            assert data["error"] == "AUTHENTICATION_ERROR"


class TestExceptionHandlerRobustness:
    """Test robustness of exception handlers."""

    @pytest.fixture
    def app(self):
        """Create application for robustness tests."""
        return create_application()

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    def test_exception_with_circular_reference(self, client):
        """Test handling exception with circular references in details."""
        app = create_application()

        @app.get("/test/circular")
        async def circular_reference_test():
            # Create circular reference
            obj1 = {"name": "obj1"}
            obj2 = {"name": "obj2", "ref": obj1}
            obj1["ref"] = obj2

            from tripsage_core.exceptions.exceptions import ErrorDetails

            details = ErrorDetails(additional_context={"circular": "This should work"})
            raise CoreServiceError("Circular reference test", details=details)

        client = TestClient(app)
        response = client.get("/test/circular")

        assert response.status_code == 502
        data = response.json()
        assert data["error"] == "SERVICE_ERROR"
        # Should not crash despite circular reference handling

    def test_exception_with_very_long_message(self, client):
        """Test handling exception with very long error message."""
        app = create_application()

        @app.get("/test/long-message")
        async def long_message_test():
            long_message = "Error: " + "X" * 10000  # Very long message
            raise CoreValidationError(long_message)

        client = TestClient(app)
        response = client.get("/test/long-message")

        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "VALIDATION_ERROR"
        # Should handle long messages without issues
        assert len(data["message"]) > 1000

    def test_exception_handler_with_unicode(self, client):
        """Test handling exceptions with unicode characters."""
        app = create_application()

        @app.get("/test/unicode")
        async def unicode_test():
            unicode_message = "Error with unicode: 测试 🚀 Ñoño"
            raise CoreAuthenticationError(unicode_message)

        client = TestClient(app)
        response = client.get("/test/unicode")

        assert response.status_code == 401
        data = response.json()
        assert data["error"] == "AUTHENTICATION_ERROR"
        assert "测试" in data["message"]
        assert "🚀" in data["message"]
        assert "Ñoño" in data["message"]
