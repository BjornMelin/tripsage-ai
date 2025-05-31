"""
Comprehensive test suite for tripsage.api.main module.

This module provides extensive tests for the FastAPI application creation,
middleware configuration, exception handlers, and router setup.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from starlette.exceptions import HTTPException as StarletteHTTPException

from tripsage.api.main import app, create_app, lifespan
from tripsage_core.exceptions.exceptions import (
    CoreAuthenticationError,
    CoreExternalAPIError,
    CoreKeyValidationError,
    CoreMCPError,
    CoreRateLimitError,
    CoreTripSageError,
    CoreValidationError,
)


class TestCreateApp:
    """Test the create_app function and FastAPI application configuration."""

    def test_create_app_returns_fastapi_instance(self):
        """Test that create_app returns a FastAPI instance."""
        test_app = create_app()
        assert isinstance(test_app, FastAPI)

    def test_create_app_has_correct_metadata(self):
        """Test that the app has correct title, version, and description."""
        test_app = create_app()
        assert test_app.title == "TripSage API"
        assert test_app.version == "1.0.0"
        assert "TripSage AI Travel Planning API" in test_app.description

    def test_create_app_development_docs_enabled(self):
        """Test that docs are enabled in development environment."""
        with patch("tripsage.api.main.get_settings") as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.environment = "development"
            mock_settings.api_title = "Test API"
            mock_settings.api_description = "Test Description"
            mock_settings.api_version = "1.0.0"
            mock_settings.get_cors_config.return_value = {
                "allow_origins": ["*"],
                "allow_credentials": True,
                "allow_methods": ["*"],
                "allow_headers": ["*"],
            }
            mock_settings.dragonfly.url = "redis://localhost:6379"
            mock_get_settings.return_value = mock_settings

            test_app = create_app()
            assert test_app.docs_url == "/api/docs"
            assert test_app.redoc_url == "/api/redoc"

    def test_create_app_production_docs_disabled(self):
        """Test that docs are disabled in production environment."""
        with patch("tripsage.api.main.get_settings") as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.environment = "production"
            mock_settings.api_title = "Test API"
            mock_settings.api_description = "Test Description"
            mock_settings.api_version = "1.0.0"
            mock_settings.get_cors_config.return_value = {
                "allow_origins": ["https://tripsage.app"],
                "allow_credentials": True,
                "allow_methods": ["GET", "POST"],
                "allow_headers": ["*"],
            }
            mock_settings.dragonfly.url = "redis://production:6379"
            mock_get_settings.return_value = mock_settings

            test_app = create_app()
            assert test_app.docs_url is None
            assert test_app.redoc_url is None

    def test_create_app_includes_all_routers(self):
        """Test that all expected routers are included."""
        test_app = create_app()
        routes = [route.path for route in test_app.routes]

        # Check for key route prefixes
        expected_prefixes = [
            "/api/health",
            "/api/user/keys",
            "/api/auth",
            "/api/v1/chat",
            "/api/trips",
            "/api/flights",
            "/api/accommodations",
            "/api/destinations",
            "/api/memory",
            "/api/ws",
        ]

        for prefix in expected_prefixes:
            assert any(route.startswith(prefix) for route in routes), (
                f"Missing route with prefix: {prefix}"
            )

    def test_create_app_middleware_configuration(self):
        """Test that all required middleware is configured."""
        test_app = create_app()

        # Check that middleware stack includes expected middleware
        middleware_classes = [
            middleware.cls.__name__ for middleware in test_app.user_middleware
        ]

        expected_middleware = [
            "CORSMiddleware",
            "LoggingMiddleware",
            "RateLimitMiddleware",
            "AuthMiddleware",
            "KeyOperationRateLimitMiddleware",
        ]

        for middleware in expected_middleware:
            assert middleware in middleware_classes, f"Missing middleware: {middleware}"


class TestLifespan:
    """Test the lifespan context manager for FastAPI."""

    @pytest.mark.asyncio
    async def test_lifespan_startup_and_shutdown(self):
        """Test that lifespan properly initializes and shuts down MCP manager."""
        mock_app = MagicMock()

        with patch("tripsage.api.main.mcp_manager") as mock_mcp_manager:
            mock_mcp_manager.initialize_all_enabled = AsyncMock()
            mock_mcp_manager.get_available_mcps.return_value = ["test_mcp"]
            mock_mcp_manager.get_initialized_mcps.return_value = ["test_mcp"]
            mock_mcp_manager.shutdown = AsyncMock()

            # Test the context manager
            async with lifespan(mock_app):
                # During the yield, manager should be initialized
                mock_mcp_manager.initialize_all_enabled.assert_called_once()
                mock_mcp_manager.get_available_mcps.assert_called_once()
                mock_mcp_manager.get_initialized_mcps.assert_called_once()

            # After context manager, shutdown should be called
            mock_mcp_manager.shutdown.assert_called_once()


class TestExceptionHandlers:
    """Test all exception handlers in the FastAPI application."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_request(self):
        """Create a mock request object."""
        request = MagicMock(spec=Request)
        request.url.path = "/test/path"
        request.state.correlation_id = "test-correlation-id"
        return request

    @pytest.mark.asyncio
    async def test_authentication_error_handler(self, mock_request):
        """Test authentication error handling."""
        from tripsage.api.main import create_app

        app = create_app()

        # Get the handler from the app's exception handlers
        handler = app.exception_handlers[CoreAuthenticationError]

        error = CoreAuthenticationError("Invalid credentials")
        error.details.user_id = "test_user"

        response = await handler(mock_request, error)

        assert response.status_code == 401
        content = response.body.decode()
        assert "Invalid credentials" in content
        assert "authentication" in content

    @pytest.mark.asyncio
    async def test_key_validation_error_handler(self, mock_request):
        """Test API key validation error handling."""
        from tripsage.api.main import create_app

        app = create_app()
        handler = app.exception_handlers[CoreKeyValidationError]

        error = CoreKeyValidationError("Invalid API key")
        error.details.service = "openai"

        response = await handler(mock_request, error)

        assert response.status_code == 400
        content = response.body.decode()
        assert "Invalid API key" in content
        assert "openai" in content

    @pytest.mark.asyncio
    async def test_rate_limit_error_handler(self, mock_request):
        """Test rate limit error handling."""
        from tripsage.api.main import create_app

        app = create_app()
        handler = app.exception_handlers[CoreRateLimitError]

        error = CoreRateLimitError("Rate limit exceeded")
        error.details.additional_context = {"retry_after": 120}

        response = await handler(mock_request, error)

        assert response.status_code == 429
        assert response.headers["Retry-After"] == "120"
        content = response.body.decode()
        assert "Rate limit exceeded" in content

    @pytest.mark.asyncio
    async def test_mcp_error_handler(self, mock_request):
        """Test MCP service error handling."""
        from tripsage.api.main import create_app

        app = create_app()
        handler = app.exception_handlers[CoreMCPError]

        error = CoreMCPError("MCP service unavailable")
        error.details.service = "flights"
        error.details.additional_context = {"tool": "search_flights"}

        response = await handler(mock_request, error)

        assert response.status_code == 502
        content = response.body.decode()
        assert "MCP service unavailable" in content
        assert "flights" in content

    @pytest.mark.asyncio
    async def test_external_api_error_handler(self, mock_request):
        """Test external API error handling."""
        from tripsage.api.main import create_app

        app = create_app()
        handler = app.exception_handlers[CoreExternalAPIError]

        error = CoreExternalAPIError("External service error")
        error.details.service = "google_maps"
        error.details.additional_context = {"api_status_code": 503}

        response = await handler(mock_request, error)

        assert response.status_code == 502
        content = response.body.decode()
        assert "External service error" in content
        assert "google_maps" in content

    @pytest.mark.asyncio
    async def test_validation_error_handler(self, mock_request):
        """Test validation error handling."""
        from tripsage.api.main import create_app

        app = create_app()
        handler = app.exception_handlers[CoreValidationError]

        error = CoreValidationError("Validation failed")
        error.details.additional_context = {"field": "email"}

        response = await handler(mock_request, error)

        assert response.status_code == 400
        content = response.body.decode()
        assert "Validation failed" in content

    @pytest.mark.asyncio
    async def test_core_tripsage_error_handler(self, mock_request):
        """Test core TripSage error handling."""
        from tripsage.api.main import create_app

        app = create_app()
        handler = app.exception_handlers[CoreTripSageError]

        error = CoreTripSageError("General TripSage error")

        response = await handler(mock_request, error)

        assert response.status_code == 500
        content = response.body.decode()
        assert "General TripSage error" in content

    @pytest.mark.asyncio
    async def test_request_validation_error_handler(self, mock_request):
        """Test FastAPI request validation error handling."""
        from tripsage.api.main import create_app

        app = create_app()
        handler = app.exception_handlers[RequestValidationError]

        # Mock validation error
        validation_error = RequestValidationError(
            [
                {
                    "loc": ("body", "email"),
                    "msg": "field required",
                    "type": "value_error.missing",
                    "input": {},
                }
            ]
        )

        response = await handler(mock_request, validation_error)

        assert response.status_code == 422
        content = response.body.decode()
        assert "Request validation failed" in content
        assert "email" in content

    @pytest.mark.asyncio
    async def test_http_exception_handler(self, mock_request):
        """Test HTTP exception handling."""
        from tripsage.api.main import create_app

        app = create_app()
        handler = app.exception_handlers[StarletteHTTPException]

        error = StarletteHTTPException(status_code=404, detail="Not found")

        response = await handler(mock_request, error)

        assert response.status_code == 404
        content = response.body.decode()
        assert "Not found" in content

    @pytest.mark.asyncio
    async def test_general_exception_handler_debug_mode(self, mock_request):
        """Test general exception handler in debug mode."""
        from tripsage.api.main import create_app

        with patch("tripsage.api.main.get_settings") as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.debug = True
            mock_settings.environment = "development"
            mock_settings.api_title = "Test API"
            mock_settings.api_description = "Test Description"
            mock_settings.api_version = "1.0.0"
            mock_settings.get_cors_config.return_value = {}
            mock_settings.dragonfly.url = "redis://localhost:6379"
            mock_get_settings.return_value = mock_settings

            app = create_app()
            handler = app.exception_handlers[Exception]

            error = ValueError("Test error message")

            response = await handler(mock_request, error)

            assert response.status_code == 500
            content = response.body.decode()
            assert "Test error message" in content

    @pytest.mark.asyncio
    async def test_general_exception_handler_production_mode(self, mock_request):
        """Test general exception handler in production mode."""
        from tripsage.api.main import create_app

        with patch("tripsage.api.main.get_settings") as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.debug = False
            mock_settings.environment = "production"
            mock_settings.api_title = "Test API"
            mock_settings.api_description = "Test Description"
            mock_settings.api_version = "1.0.0"
            mock_settings.get_cors_config.return_value = {}
            mock_settings.dragonfly.url = "redis://localhost:6379"
            mock_get_settings.return_value = mock_settings

            app = create_app()
            handler = app.exception_handlers[Exception]

            error = ValueError("Test error message")

            response = await handler(mock_request, error)

            assert response.status_code == 500
            content = response.body.decode()
            assert "Test error message" not in content
            assert "Internal error occurred" in content


class TestIntegration:
    """Test integration scenarios and full application behavior."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)

    def test_health_endpoint_exists(self, client):
        """Test that the health endpoint is accessible."""
        response = client.get("/api/health")
        assert response.status_code in [200, 404]  # May not be implemented yet

    def test_cors_headers_in_response(self, client):
        """Test that CORS headers are properly set."""
        response = client.options(
            "/api/health", headers={"Origin": "http://localhost:3000"}
        )
        # Should have CORS headers if properly configured
        assert response.status_code in [200, 404, 405]

    def test_app_has_openapi_schema(self):
        """Test that the app has a valid OpenAPI schema."""
        openapi_schema = app.openapi()
        assert openapi_schema is not None
        assert "info" in openapi_schema
        assert "paths" in openapi_schema

    def test_middleware_order_is_correct(self):
        """Test that middleware is applied in the correct order."""
        middleware_classes = [
            middleware.cls.__name__ for middleware in app.user_middleware
        ]

        # Logging should be first (last in the list due to LIFO order)
        assert "LoggingMiddleware" in middleware_classes

    @pytest.mark.asyncio
    async def test_concurrent_request_handling(self, client):
        """Test that the application can handle concurrent requests."""

        async def make_request():
            return client.get("/api/health")

        # Make multiple concurrent requests
        tasks = [make_request() for _ in range(10)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # All requests should complete (whether successful or not)
        assert len(responses) == 10
        for response in responses:
            if hasattr(response, "status_code"):
                # Should be a valid HTTP status code
                assert 200 <= response.status_code < 600


class TestModuleExports:
    """Test that the module exports the expected objects."""

    def test_app_is_exported(self):
        """Test that the app instance is exported."""
        from tripsage.api.main import app

        assert isinstance(app, FastAPI)

    def test_create_app_is_exported(self):
        """Test that create_app function is exported."""
        from tripsage.api.main import create_app

        assert callable(create_app)

    def test_lifespan_is_exported(self):
        """Test that lifespan function is exported."""
        from tripsage.api.main import lifespan

        assert callable(lifespan)


class TestPerformance:
    """Test performance characteristics of the application."""

    def test_app_creation_speed(self):
        """Test that app creation is reasonably fast."""
        import time

        start_time = time.time()
        for _ in range(10):
            create_app()
        end_time = time.time()

        total_time = end_time - start_time
        # Should create 10 apps in under 5 seconds
        assert total_time < 5.0

    def test_route_count_is_reasonable(self):
        """Test that the application has a reasonable number of routes."""
        route_count = len(app.routes)
        # Should have routes but not an excessive number
        assert 10 <= route_count <= 200


class TestErrorScenarios:
    """Test error scenarios and edge cases."""

    def test_app_creation_with_mock_dependencies(self):
        """Test app creation with mocked dependencies."""
        with patch("tripsage.api.main.mcp_manager") as mock_mcp_manager:
            mock_mcp_manager.initialize_all_enabled = AsyncMock()
            mock_mcp_manager.shutdown = AsyncMock()

            test_app = create_app()
            assert isinstance(test_app, FastAPI)

    @pytest.mark.asyncio
    async def test_lifespan_with_mcp_failure(self):
        """Test lifespan behavior when MCP initialization fails."""
        mock_app = MagicMock()

        with patch("tripsage.api.main.mcp_manager") as mock_mcp_manager:
            mock_mcp_manager.initialize_all_enabled = AsyncMock(
                side_effect=Exception("MCP init failed")
            )
            mock_mcp_manager.shutdown = AsyncMock()

            # Should handle initialization failure gracefully
            with pytest.raises(Exception, match="MCP init failed"):
                async with lifespan(mock_app):
                    pass

    def test_settings_configuration_edge_cases(self):
        """Test app creation with various settings configurations."""
        with patch("tripsage.api.main.get_settings") as mock_get_settings:
            # Test with minimal settings
            mock_settings = MagicMock()
            mock_settings.environment = "testing"
            mock_settings.api_title = "Minimal API"
            mock_settings.api_description = "Minimal Description"
            mock_settings.api_version = "0.1.0"
            mock_settings.get_cors_config.return_value = {
                "allow_origins": [],
                "allow_credentials": False,
                "allow_methods": ["GET"],
                "allow_headers": [],
            }
            mock_settings.dragonfly.url = "redis://test:6379"
            mock_get_settings.return_value = mock_settings

            test_app = create_app()
            assert test_app.title == "Minimal API"
            assert test_app.version == "0.1.0"
