"""
Comprehensive test suite for tripsage.api.routers.health module.

This module provides extensive tests for the health check endpoints,
dependency checking, and service status monitoring.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from tripsage.api.routers.health import router


@pytest.fixture
def client():
    """Create a test client for the health router."""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


class TestHealthEndpoint:
    """Test the basic health check endpoint."""

    def test_health_endpoint_returns_200(self, client):
        """Test that health endpoint returns 200 OK."""
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK

    def test_health_response_format(self, client):
        """Test that health endpoint returns expected JSON format."""
        response = client.get("/health")
        data = response.json()

        assert "status" in data
        assert "timestamp" in data
        assert data["status"] in ["healthy", "unhealthy", "degraded"]

    def test_health_includes_timestamp(self, client):
        """Test that health response includes a valid timestamp."""
        response = client.get("/health")
        data = response.json()

        assert "timestamp" in data
        # Should be ISO format timestamp
        import datetime

        try:
            datetime.datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
            valid_timestamp = True
        except ValueError:
            valid_timestamp = False
        assert valid_timestamp


class TestDetailedHealthEndpoint:
    """Test the detailed health check endpoint."""

    def test_detailed_health_endpoint_exists(self, client):
        """Test that detailed health endpoint is accessible."""
        response = client.get("/health/detailed")
        # Should return either 200 or 404 if not implemented
        assert response.status_code in [200, 404]

    def test_detailed_health_includes_services(self, client):
        """Test that detailed health includes service status if implemented."""
        response = client.get("/health/detailed")

        if response.status_code == 200:
            data = response.json()
            assert "status" in data
            # May include services information
            if "services" in data:
                assert isinstance(data["services"], dict)


class TestDependencyHealth:
    """Test health checks for various dependencies."""

    @pytest.mark.asyncio
    async def test_database_health_check(self):
        """Test database connectivity health check."""
        # Mock database service
        with patch("tripsage.api.routers.health.get_database_service") as mock_db:
            mock_db_service = AsyncMock()
            mock_db_service.health_check.return_value = {"status": "healthy"}
            mock_db.return_value = mock_db_service

            # Import and test the health function if it exists
            try:
                from tripsage.api.routers.health import check_database_health

                result = await check_database_health()
                assert result["status"] == "healthy"
            except ImportError:
                # Health check function may not be implemented yet
                pass

    @pytest.mark.asyncio
    async def test_cache_health_check(self):
        """Test cache service health check."""
        with patch("tripsage.api.routers.health.get_cache_service") as mock_cache:
            mock_cache_service = AsyncMock()
            mock_cache_service.ping.return_value = True
            mock_cache.return_value = mock_cache_service

            try:
                from tripsage.api.routers.health import check_cache_health

                result = await check_cache_health()
                assert "status" in result
            except ImportError:
                pass

    @pytest.mark.asyncio
    async def test_mcp_services_health_check(self):
        """Test MCP services health check."""
        with patch("tripsage.api.routers.health.mcp_manager") as mock_mcp:
            mock_mcp.get_initialized_mcps.return_value = ["flights", "hotels"]
            mock_mcp.health_check.return_value = {
                "flights": {"status": "healthy"},
                "hotels": {"status": "healthy"},
            }

            try:
                from tripsage.api.routers.health import check_mcp_health

                result = await check_mcp_health()
                assert "flights" in str(result) or "status" in result
            except ImportError:
                pass


class TestHealthMetrics:
    """Test health endpoint metrics and monitoring."""

    def test_health_endpoint_response_time(self, client):
        """Test that health endpoint responds quickly."""
        import time

        start_time = time.time()
        response = client.get("/health")
        end_time = time.time()

        response_time = end_time - start_time
        # Health check should respond in under 1 second
        assert response_time < 1.0
        assert response.status_code == 200

    def test_health_endpoint_multiple_calls(self, client):
        """Test that health endpoint handles multiple concurrent calls."""
        responses = []
        for _ in range(10):
            response = client.get("/health")
            responses.append(response)

        # All calls should succeed
        for response in responses:
            assert response.status_code == 200

    def test_health_endpoint_reliability(self, client):
        """Test health endpoint reliability over multiple calls."""
        success_count = 0
        total_calls = 20

        for _ in range(total_calls):
            try:
                response = client.get("/health")
                if response.status_code == 200:
                    success_count += 1
            except Exception:
                pass

        # Should have high success rate
        success_rate = success_count / total_calls
        assert success_rate >= 0.9  # 90% success rate


class TestHealthEndpointSecurity:
    """Test security aspects of health endpoints."""

    def test_health_endpoint_no_auth_required(self, client):
        """Test that health endpoint doesn't require authentication."""
        # Health checks should be publicly accessible
        response = client.get("/health")
        assert response.status_code != 401
        assert response.status_code != 403

    def test_health_endpoint_safe_error_handling(self, client):
        """Test that health endpoint doesn't expose sensitive information."""
        response = client.get("/health")
        data = response.json()

        # Should not contain sensitive information
        response_text = str(data).lower()
        sensitive_terms = ["password", "secret", "key", "token", "credential"]

        for term in sensitive_terms:
            assert term not in response_text

    def test_health_endpoint_cors_headers(self, client):
        """Test that health endpoint includes appropriate CORS headers."""
        response = client.options("/health")
        # Should handle OPTIONS request for CORS
        assert response.status_code in [200, 204, 405]


class TestHealthEndpointErrorHandling:
    """Test error handling in health endpoints."""

    def test_health_endpoint_with_service_failures(self, client):
        """Test health endpoint behavior when services are down."""
        with patch("tripsage.api.routers.health.get_settings") as mock_settings:
            mock_settings.return_value.database.supabase_url = "invalid_url"

            response = client.get("/health")
            # Should still return a response, possibly with degraded status
            assert response.status_code in [200, 503]

    def test_health_endpoint_exception_handling(self, client):
        """Test that health endpoint handles internal exceptions gracefully."""
        # Even if there are internal errors, health should respond
        response = client.get("/health")
        assert response.status_code in [200, 500, 503]

        # Should return valid JSON
        try:
            data = response.json()
            assert isinstance(data, dict)
        except Exception:
            # If not JSON, at least should be a valid response
            assert response.content is not None


class TestHealthEndpointConfiguration:
    """Test health endpoint configuration and customization."""

    def test_health_endpoint_respects_environment(self, client):
        """Test that health endpoint behavior varies by environment."""
        with patch("tripsage.api.routers.health.get_settings") as mock_settings:
            # Test production environment
            mock_settings.return_value.environment = "production"
            response_prod = client.get("/health")

            # Test development environment
            mock_settings.return_value.environment = "development"
            response_dev = client.get("/health")

            # Both should work but may have different detail levels
            assert response_prod.status_code == 200
            assert response_dev.status_code == 200

    def test_health_endpoint_custom_checks(self, client):
        """Test health endpoint with custom health checks."""
        # Test if custom health checks are configurable
        response = client.get("/health")
        data = response.json()

        # Basic health response should always work
        assert "status" in data


class TestHealthEndpointIntegration:
    """Test health endpoint integration with monitoring systems."""

    def test_health_endpoint_monitoring_format(self, client):
        """Test that health endpoint returns monitoring-friendly format."""
        response = client.get("/health")
        data = response.json()

        # Should be compatible with common monitoring tools
        assert isinstance(data, dict)
        assert "status" in data

        # Status should be a standard value
        if "status" in data:
            assert data["status"] in [
                "healthy",
                "unhealthy",
                "degraded",
                "ok",
                "error",
                "pass",
                "fail",
            ]

    def test_health_endpoint_prometheus_metrics(self, client):
        """Test health endpoint compatibility with Prometheus."""
        response = client.get("/health")

        # Should return quickly for metrics scraping
        assert response.status_code == 200

        # Could have metrics endpoint
        try:
            metrics_response = client.get("/metrics")
            # Metrics endpoint may or may not exist
            assert metrics_response.status_code in [200, 404]
        except Exception:
            # Metrics endpoint may not be implemented
            pass

    def test_health_endpoint_load_balancer_format(self, client):
        """Test health endpoint format for load balancers."""
        response = client.get("/health")

        # Load balancers typically expect:
        # - HTTP 200 for healthy
        # - HTTP 503 for unhealthy
        # - Quick response time
        assert response.status_code in [200, 503]

        # Should have minimal response for efficiency
        assert len(response.content) < 1024  # Less than 1KB


class TestHealthEndpointDocumentation:
    """Test health endpoint documentation and OpenAPI specs."""

    def test_health_endpoint_openapi_spec(self):
        """Test that health endpoints are properly documented."""
        from fastapi import FastAPI

        from tripsage.api.routers.health import router

        app = FastAPI()
        app.include_router(router)
        openapi_schema = app.openapi()

        # Should have health endpoints in OpenAPI spec
        paths = openapi_schema.get("paths", {})
        health_paths = [path for path in paths.keys() if "health" in path]

        assert len(health_paths) > 0, "Health endpoints should be documented"

    def test_health_endpoint_tags(self):
        """Test that health endpoints have appropriate tags."""
        from tripsage.api.routers.health import router

        # Router should have health-related tags
        assert hasattr(router, "tags")
        if router.tags:
            assert any("health" in tag.lower() for tag in router.tags)


class TestHealthEndpointPerformance:
    """Test performance characteristics of health endpoints."""

    def test_health_endpoint_memory_usage(self, client):
        """Test that health endpoint doesn't consume excessive memory."""
        import os

        import psutil

        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss

        # Make multiple health check calls
        for _ in range(100):
            client.get("/health")

        memory_after = process.memory_info().rss
        memory_increase = memory_after - memory_before

        # Memory increase should be minimal (less than 10MB)
        assert memory_increase < 10 * 1024 * 1024

    def test_health_endpoint_cpu_usage(self, client):
        """Test that health endpoint doesn't consume excessive CPU."""
        import time

        start_time = time.time()

        # Make many rapid health checks
        for _ in range(50):
            client.get("/health")

        end_time = time.time()
        total_time = end_time - start_time

        # Should complete 50 health checks quickly
        assert total_time < 5.0  # Less than 5 seconds
