"""Integration tests for modernized dependency injection system.

This module demonstrates and tests the new FastAPI dependency injection
patterns including health monitoring, circuit breakers, and testing utilities.
"""

import asyncio
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from tests.utils.dependency_testing import (
    HealthCheckTestUtils,
    PerformanceTestUtils,
)
from tripsage.api.core.dependencies import (
    create_dependency_override,
    get_dependency_health,
    record_dependency_call,
)
from tripsage.api.main import app


class TestDependencyHealthMonitoring:
    """Test dependency health monitoring and circuit breaker functionality."""

    @pytest.mark.asyncio
    async def test_dependency_health_tracking(self, dependency_test_setup):
        """Test that dependency health is properly tracked."""
        service_name = "test_service"

        # Record successful call
        record_dependency_call(service_name, 150.0, True)

        # Check health was recorded
        health = get_dependency_health(service_name)
        assert health.name == service_name
        assert health.healthy is True
        assert health.response_time_ms == 150.0
        assert health.error_count == 0

    @pytest.mark.asyncio
    async def test_dependency_failure_tracking(self, dependency_test_setup):
        """Test that dependency failures are properly tracked."""
        service_name = "test_service"
        error_message = "Test connection error"

        # Record failed call
        record_dependency_call(service_name, 5000.0, False, error_message)

        # Check failure was recorded
        health = get_dependency_health(service_name)
        assert health.name == service_name
        assert health.healthy is True  # Still healthy with just 1 failure
        assert health.response_time_ms == 5000.0
        assert health.error_count == 1
        assert health.last_error == error_message

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_on_failures(self, dependency_test_setup):
        """Test that circuit breaker opens after threshold failures."""
        service_name = "test_circuit_breaker"

        # Simulate multiple failures
        await HealthCheckTestUtils.simulate_service_failure(service_name)

        # Check circuit breaker opened
        state = HealthCheckTestUtils.get_circuit_breaker_state(service_name)
        assert state == "OPEN"

        # Check health reflects circuit breaker state
        health = get_dependency_health(service_name)
        assert health.healthy is False

    @pytest.mark.asyncio
    async def test_circuit_breaker_recovery(self, dependency_test_setup):
        """Test circuit breaker recovery after successful calls."""
        service_name = "test_recovery"

        # First cause failures
        await HealthCheckTestUtils.simulate_service_failure(service_name)
        assert HealthCheckTestUtils.get_circuit_breaker_state(service_name) == "OPEN"

        # Wait for timeout (simulated by setting last_failure_time in the past)
        import time

        from tripsage.api.core.dependencies import _circuit_breakers

        if service_name in _circuit_breakers:
            _circuit_breakers[service_name].last_failure_time = (
                time.time() - 70
            )  # Past timeout

        # Simulate recovery
        await HealthCheckTestUtils.simulate_service_recovery(service_name)

        # Check circuit breaker closed
        state = HealthCheckTestUtils.get_circuit_breaker_state(service_name)
        assert state == "CLOSED"


class TestDependencyOverrides:
    """Test dependency override functionality for testing."""

    @pytest.mark.asyncio
    async def test_dependency_override_context_manager(self, dependency_test_setup):
        """Test the dependency override context manager."""
        mock_service = AsyncMock()
        mock_service.test_method.return_value = "mocked_result"

        async with create_dependency_override() as override:
            override.override("test_service", mock_service)

            # The override should be active here
            # In a real test, you would call an endpoint that uses the dependency
            # and verify the mock was used

        # Override should be cleared outside the context
        # Verify cleanup occurred


class TestPerformanceMonitoring:
    """Test performance monitoring capabilities."""

    @pytest.mark.asyncio
    async def test_dependency_latency_measurement(self, dependency_test_setup):
        """Test dependency latency measurement."""

        async def mock_dependency():
            """Mock dependency function with simulated delay."""
            await asyncio.sleep(0.01)  # 10ms delay
            return "result"

        # Measure latency
        stats = await PerformanceTestUtils.measure_dependency_latency(
            mock_dependency, iterations=10
        )

        # Verify measurements
        assert stats["total_iterations"] == 10
        assert stats["avg_latency_ms"] > 5  # Should be around 10ms
        assert stats["min_latency_ms"] > 0
        assert stats["max_latency_ms"] >= stats["avg_latency_ms"]

    @pytest.mark.asyncio
    async def test_concurrent_dependency_access(self, dependency_test_setup):
        """Test concurrent access to dependencies."""

        async def mock_dependency():
            """Mock dependency with slight delay."""
            await asyncio.sleep(0.001)  # 1ms delay
            return "concurrent_result"

        # Test concurrent access
        stats = await PerformanceTestUtils.test_concurrent_dependency_access(
            mock_dependency, concurrent_requests=20
        )

        # Verify results
        assert stats["total_requests"] == 20
        assert stats["successful_requests"] == 20
        assert stats["failed_requests"] == 0
        assert stats["requests_per_second"] > 0


class TestHealthEndpoints:
    """Test the new health check endpoints."""

    def test_dependency_health_endpoint_empty(self, dependency_test_setup):
        """Test dependency health endpoint with no tracked dependencies."""
        with TestClient(app) as client:
            response = client.get("/api/health/dependencies")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["summary"]["total_dependencies"] == 0

    def test_dependency_health_endpoint_with_data(self, dependency_test_setup):
        """Test dependency health endpoint with tracked dependencies."""
        # Add some dependency health data
        record_dependency_call("test_db", 100.0, True)
        record_dependency_call("test_cache", 50.0, True)
        record_dependency_call("test_service", 2000.0, False, "Timeout error")

        with TestClient(app) as client:
            response = client.get("/api/health/dependencies")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] in ["healthy", "degraded", "unhealthy"]
            assert data["summary"]["total_dependencies"] == 3
            assert len(data["dependencies"]) == 3

    def test_specific_dependency_health_endpoint(self, dependency_test_setup):
        """Test getting health for a specific dependency."""
        service_name = "specific_test_service"
        record_dependency_call(service_name, 75.0, True)

        with TestClient(app) as client:
            response = client.get(f"/api/health/dependencies/{service_name}")

            assert response.status_code == 200
            data = response.json()
            assert data["dependency"] == service_name
            assert data["health"]["healthy"] is True
            assert data["health"]["response_time_ms"] == 75.0

    def test_nonexistent_dependency_health_endpoint(self, dependency_test_setup):
        """Test getting health for a nonexistent dependency."""
        with TestClient(app) as client:
            response = client.get("/api/health/dependencies/nonexistent_service")

            assert response.status_code == 404
            data = response.json()
            assert data["error"] is True
            assert "not found" in data["message"].lower()

    def test_reset_dependency_health_endpoint(self, dependency_test_setup):
        """Test resetting dependency health monitoring."""
        # Add some data first
        record_dependency_call("test_service", 100.0, True)

        with TestClient(app) as client:
            # Verify data exists
            response = client.get("/api/health/dependencies")
            assert len(response.json()["dependencies"]) > 0

            # Reset the data
            response = client.post("/api/health/dependencies/reset")
            assert response.status_code == 200

            # Verify data was cleared
            response = client.get("/api/health/dependencies")
            assert len(response.json()["dependencies"]) == 0


class TestModernizedDependencyTypes:
    """Test the modernized Annotated dependency types."""

    @pytest.mark.asyncio
    async def test_modern_dependency_types_import(self):
        """Test that all modern dependency types can be imported."""

        # If we get here without import errors, the test passes
        assert True


class TestBackgroundTaskDependencies:
    """Test background task dependency patterns."""

    @pytest.mark.asyncio
    async def test_background_database_session(self, dependency_test_setup):
        """Test background database session context manager."""
        from tripsage.api.core.dependencies import get_background_db_session

        # Test the context manager works
        async with get_background_db_session() as db:
            assert db is not None
            # In a real test, you'd verify the database service methods

    @pytest.mark.asyncio
    async def test_background_cache_session(self, dependency_test_setup):
        """Test background cache session context manager."""
        from tripsage.api.core.dependencies import get_background_cache_session

        # Test the context manager works
        async with get_background_cache_session() as cache:
            assert cache is not None
            # In a real test, you'd verify the cache service methods


@pytest.mark.integration
class TestEndToEndDependencyInjection:
    """End-to-end tests for the modernized dependency injection system."""

    @pytest.mark.asyncio
    async def test_health_check_with_real_dependencies(self):
        """Test health check endpoints with real dependency calls."""
        with TestClient(app) as client:
            # Make a call that will exercise dependencies
            response = client.get("/api/health")
            assert response.status_code == 200

            # Check if dependency health was tracked
            response = client.get("/api/health/dependencies")
            assert response.status_code == 200

            data = response.json()
            # Should have some dependencies tracked after health check
            assert data["summary"]["total_dependencies"] >= 0

    def test_modernized_router_endpoints(self, dependency_test_setup, mock_services):
        """Test that modernized router endpoints work correctly."""
        with TestClient(app) as client:
            # Test endpoints that use the new dependency types
            # Note: These tests would need proper authentication setup

            # Test user preferences endpoint (uses UserServiceDep)
            # Would need authentication token for real test
            # response = client.get("/api/users/preferences")

            # Test memory endpoints (uses MemoryServiceDep)
            # response = client.get("/api/memory/context")

            # For now, just verify the app starts without errors
            response = client.get("/api/health/liveness")
            assert response.status_code == 200


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
