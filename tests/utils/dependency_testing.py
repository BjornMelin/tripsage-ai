"""Testing utilities for FastAPI dependency injection.

This module provides utilities for testing FastAPI dependencies with mocking
and override capabilities following modern testing patterns.

Example usage:
    ```python
    async def test_chat_endpoint():
        # Create mock service
        mock_chat_service = AsyncMock()
        mock_chat_service.chat_completion.return_value = ChatResponse(...)

        # Override dependency
        async with create_dependency_override() as override:
            override.override("chat_service", mock_chat_service)

            # Test the endpoint
            response = await client.post("/api/chat", json={...})
            assert response.status_code == 200
    ```
"""

import asyncio
import logging
import time
from typing import Any, Dict
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient

from tripsage.api.core.dependencies import (
    create_dependency_override,
    reset_dependency_health,
)

logger = logging.getLogger(__name__)


class MockServiceFactory:
    """Factory for creating mock services with common patterns."""

    @staticmethod
    def create_database_service_mock():
        """Create a mock database service."""
        mock = AsyncMock()
        mock.execute_query.return_value = [{"id": 1, "test": "data"}]
        mock.get_pool_stats.return_value = {
            "active_connections": 5,
            "idle_connections": 10,
            "total_connections": 15,
        }
        return mock

    @staticmethod
    def create_cache_service_mock():
        """Create a mock cache service."""
        mock = AsyncMock()
        mock.get.return_value = None
        mock.set.return_value = True
        mock.delete.return_value = True
        mock.ping.return_value = True
        return mock

    @staticmethod
    def create_user_service_mock():
        """Create a mock user service."""
        mock = AsyncMock()
        mock.get_user_by_id.return_value = {
            "id": "test-user-id",
            "email": "test@example.com",
            "full_name": "Test User",
            "preferences": {},
        }
        mock.create_user.return_value = {
            "id": "new-user-id",
            "email": "new@example.com",
            "full_name": "New User",
        }
        return mock

    @staticmethod
    def create_chat_service_mock():
        """Create a mock chat service."""
        mock = AsyncMock()
        mock.chat_completion.return_value = {
            "message": "Test response",
            "session_id": "test-session-id",
        }
        mock.create_session.return_value = {
            "id": "test-session-id",
            "title": "Test Session",
        }
        return mock


class DependencyTestClient:
    """Enhanced test client with dependency override capabilities."""

    def __init__(self, app: FastAPI):
        self.app = app
        self.client = TestClient(app)
        self.async_client = None
        self._overrides: Dict[str, Any] = {}

    async def __aenter__(self):
        """Enter async context manager."""
        self.async_client = AsyncClient(app=self.app, base_url="http://test")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager."""
        if self.async_client:
            await self.async_client.aclose()
        self.clear_overrides()

    def override_dependency(self, service_name: str, mock_service: Any):
        """Override a dependency with a mock service."""
        self._overrides[service_name] = mock_service
        # Apply override to the app
        if hasattr(self.app, "dependency_overrides"):
            # This would need to be implemented based on how FastAPI
            # dependency overrides work in the specific version
            pass

    def clear_overrides(self):
        """Clear all dependency overrides."""
        self._overrides.clear()
        if hasattr(self.app, "dependency_overrides"):
            # Clear FastAPI dependency overrides
            pass


@pytest.fixture
async def dependency_test_setup():
    """Pytest fixture for setting up dependency testing."""
    # Reset dependency health before each test
    reset_dependency_health()

    yield

    # Cleanup after test
    reset_dependency_health()


@pytest.fixture
def mock_services():
    """Pytest fixture providing common mock services."""
    return {
        "database": MockServiceFactory.create_database_service_mock(),
        "cache": MockServiceFactory.create_cache_service_mock(),
        "user_service": MockServiceFactory.create_user_service_mock(),
        "chat_service": MockServiceFactory.create_chat_service_mock(),
    }


class HealthCheckTestUtils:
    """Utilities for testing dependency health monitoring."""

    @staticmethod
    async def simulate_service_failure(
        service_name: str, error_message: str = "Test error"
    ):
        """Simulate a service failure for testing circuit breaker."""
        from tripsage.api.core.dependencies import record_dependency_call

        # Record multiple failures to trigger circuit breaker
        for _ in range(6):  # Exceeds default threshold of 5
            record_dependency_call(service_name, 1000.0, False, error_message)

    @staticmethod
    async def simulate_service_recovery(service_name: str):
        """Simulate service recovery for testing circuit breaker."""
        from tripsage.api.core.dependencies import record_dependency_call

        # Record successful calls to recover the service
        for _ in range(3):
            record_dependency_call(service_name, 100.0, True)

    @staticmethod
    def get_circuit_breaker_state(service_name: str) -> str:
        """Get the current circuit breaker state for a service."""
        from tripsage.api.core.dependencies import _circuit_breakers

        if service_name not in _circuit_breakers:
            return "CLOSED"
        return _circuit_breakers[service_name].state


# Example test functions demonstrating usage


async def example_test_with_mocked_dependencies():
    """Example test showing how to use dependency mocking."""
    from tripsage.api.main import app

    # Create mock services
    mock_user_service = MockServiceFactory.create_user_service_mock()
    mock_chat_service = MockServiceFactory.create_chat_service_mock()

    # Use dependency override context
    async with create_dependency_override() as override:
        override.override("user_service", mock_user_service)
        override.override("chat_service", mock_chat_service)

        # Test with async client
        async with DependencyTestClient(app) as client:
            response = await client.async_client.get("/api/users/preferences")

            # Verify mock was called
            mock_user_service.get_user_by_id.assert_called_once()

            # Add assertions about response
            assert response.status_code == 200


async def example_test_circuit_breaker():
    """Example test for circuit breaker functionality."""
    service_name = "test_service"

    # Simulate failures
    await HealthCheckTestUtils.simulate_service_failure(service_name)

    # Check circuit breaker opened
    state = HealthCheckTestUtils.get_circuit_breaker_state(service_name)
    assert state == "OPEN"

    # Simulate recovery
    await HealthCheckTestUtils.simulate_service_recovery(service_name)

    # Check circuit breaker closed
    state = HealthCheckTestUtils.get_circuit_breaker_state(service_name)
    assert state == "CLOSED"


# Performance testing utilities


class PerformanceTestUtils:
    """Utilities for testing dependency performance."""

    @staticmethod
    async def measure_dependency_latency(dependency_func, iterations: int = 100):
        """Measure average latency of a dependency function."""
        import time

        latencies = []
        for _ in range(iterations):
            start_time = time.time()
            await dependency_func()
            end_time = time.time()
            latencies.append((end_time - start_time) * 1000)  # Convert to ms

        return {
            "avg_latency_ms": sum(latencies) / len(latencies),
            "min_latency_ms": min(latencies),
            "max_latency_ms": max(latencies),
            "total_iterations": iterations,
        }

    @staticmethod
    async def test_concurrent_dependency_access(
        dependency_func, concurrent_requests: int = 50
    ):
        """Test concurrent access to a dependency."""
        tasks = [dependency_func() for _ in range(concurrent_requests)]

        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()

        successful_requests = sum(1 for r in results if not isinstance(r, Exception))
        failed_requests = len(results) - successful_requests

        return {
            "total_requests": concurrent_requests,
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "total_time_seconds": end_time - start_time,
            "requests_per_second": concurrent_requests / (end_time - start_time),
        }
