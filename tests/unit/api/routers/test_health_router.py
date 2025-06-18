"""Comprehensive tests for enhanced health check endpoints."""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient

from tripsage.api.main import app
from tripsage.api.routers.health import (
    ComponentHealth,
    ReadinessCheck,
    SystemHealth,
)
from tripsage_core.services.business.api_key_validator import (
    ServiceHealthCheck,
    ServiceHealthStatus,
    ServiceType,
)

class TestEnhancedHealthEndpoints:
    """Test suite for enhanced health check endpoints."""

    @pytest.fixture
    async def async_client(self):
        """Create async test client."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            yield ac

    @pytest.fixture
    def mock_db_service(self):
        """Mock database service."""
        mock = AsyncMock()
        mock.execute_query.return_value = [{"health_check": 1}]
        mock.get_pool_stats.return_value = {
            "pool_size": 10,
            "checked_out": 2,
            "overflow": 0,
        }
        return mock

    @pytest.fixture
    def mock_cache_service(self):
        """Mock cache service."""
        mock = AsyncMock()
        mock.ping.return_value = True
        mock.info.return_value = {
            "used_memory_human": "1.2M",
            "connected_clients": "1",
            "total_commands_processed": "1234",
        }
        return mock

    @pytest.fixture
    def mock_settings(self):
        """Mock settings."""
        settings = Mock()
        settings.environment = "test"
        return settings

    @pytest.fixture
    def mock_validator_healthy(self):
        """Mock API key validator with healthy services."""
        validator = AsyncMock()

        # Mock health check results
        validator.check_all_services_health.return_value = {
            ServiceType.OPENAI: ServiceHealthCheck(
                service=ServiceType.OPENAI,
                status=ServiceHealthStatus.HEALTHY,
                latency_ms=150.0,
                message="OpenAI API is operational",
                details={"validation_type": "api_call"},
            ),
            ServiceType.WEATHER: ServiceHealthCheck(
                service=ServiceType.WEATHER,
                status=ServiceHealthStatus.HEALTHY,
                latency_ms=200.0,
                message="Weather API is operational",
                details={"api_version": "2.5"},
            ),
            ServiceType.GOOGLEMAPS: ServiceHealthCheck(
                service=ServiceType.GOOGLEMAPS,
                status=ServiceHealthStatus.HEALTHY,
                latency_ms=300.0,
                message="Google Maps API is operational",
                details={"status": "OK"},
            ),
        }

        validator.check_service_health.return_value = ServiceHealthCheck(
            service=ServiceType.OPENAI,
            status=ServiceHealthStatus.HEALTHY,
            latency_ms=150.0,
            message="OpenAI API is operational",
        )

        return validator

    @pytest.fixture
    def mock_validator_degraded(self):
        """Mock API key validator with degraded services."""
        validator = AsyncMock()

        validator.check_all_services_health.return_value = {
            ServiceType.OPENAI: ServiceHealthCheck(
                service=ServiceType.OPENAI,
                status=ServiceHealthStatus.HEALTHY,
                latency_ms=150.0,
                message="OpenAI API is operational",
            ),
            ServiceType.WEATHER: ServiceHealthCheck(
                service=ServiceType.WEATHER,
                status=ServiceHealthStatus.DEGRADED,
                latency_ms=800.0,
                message="Weather API experiencing delays",
                details={"status": "SLOW_RESPONSE"},
            ),
            ServiceType.GOOGLEMAPS: ServiceHealthCheck(
                service=ServiceType.GOOGLEMAPS,
                status=ServiceHealthStatus.UNHEALTHY,
                latency_ms=5000.0,
                message="Google Maps API is down",
                details={"error": "SERVICE_UNAVAILABLE"},
            ),
        }

        return validator

    async def test_comprehensive_health_check_all_healthy(
        self,
        async_client,
        mock_db_service,
        mock_cache_service,
        mock_settings,
        mock_validator_healthy,
    ):
        """Test comprehensive health check with all services healthy."""
        with (
            patch(
                "tripsage.api.routers.health.ApiKeyValidator"
            ) as mock_validator_class,
            patch(
                "tripsage.api.core.dependencies.get_database_service",
                return_value=mock_db_service,
            ),
            patch(
                "tripsage.api.core.dependencies.get_cache_service",
                return_value=mock_cache_service,
            ),
            patch(
                "tripsage.api.core.dependencies.get_settings",
                return_value=mock_settings,
            ),
        ):
            # Configure the validator context manager
            mock_validator_class.return_value.__aenter__.return_value = (
                mock_validator_healthy
            )
            mock_validator_class.return_value.__aexit__.return_value = None

            response = await async_client.get("/api/health")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            # Verify overall structure
            assert data["status"] == "healthy"
            assert data["environment"] == "test"
            assert data["version"] == "1.0.0"
            assert isinstance(data["timestamp"], str)
            assert len(data["components"]) >= 5  # app, db, cache, + external services
            assert len(data["external_services"]) == 3

            # Verify application component
            app_component = next(
                c for c in data["components"] if c["name"] == "application"
            )
            assert app_component["status"] == "healthy"
            assert app_component["message"] == "TripSage API is running"

            # Verify database component
            db_component = next(
                c for c in data["components"] if c["name"] == "database"
            )
            assert db_component["status"] == "healthy"
            assert db_component["message"] == "Database is responsive"
            assert db_component["latency_ms"] is not None

            # Verify cache component
            cache_component = next(
                c for c in data["components"] if c["name"] == "cache"
            )
            assert cache_component["status"] == "healthy"
            assert cache_component["message"] == "Cache is responsive"

            # Verify external services
            assert "openai" in data["external_services"]
            assert "weather" in data["external_services"]
            assert "googlemaps" in data["external_services"]

    async def test_comprehensive_health_check_degraded_services(
        self,
        async_client,
        mock_db_service,
        mock_cache_service,
        mock_settings,
        mock_validator_degraded,
    ):
        """Test comprehensive health check with degraded/unhealthy services."""
        with (
            patch(
                "tripsage.api.routers.health.ApiKeyValidator"
            ) as mock_validator_class,
            patch(
                "tripsage.api.core.dependencies.get_database_service",
                return_value=mock_db_service,
            ),
            patch(
                "tripsage.api.core.dependencies.get_cache_service",
                return_value=mock_cache_service,
            ),
            patch(
                "tripsage.api.core.dependencies.get_settings",
                return_value=mock_settings,
            ),
        ):
            mock_validator_class.return_value.__aenter__.return_value = (
                mock_validator_degraded
            )
            mock_validator_class.return_value.__aexit__.return_value = None

            response = await async_client.get("/api/health")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            # Overall status should be unhealthy due to Google Maps being down
            assert data["status"] == "unhealthy"

            # Verify degraded service
            weather_component = next(
                c for c in data["components"] if c["name"] == "external_weather"
            )
            assert weather_component["status"] == "degraded"
            assert weather_component["latency_ms"] == 800.0

            # Verify unhealthy service
            maps_component = next(
                c for c in data["components"] if c["name"] == "external_googlemaps"
            )
            assert maps_component["status"] == "unhealthy"
            assert maps_component["latency_ms"] == 5000.0

    async def test_comprehensive_health_check_database_failure(
        self, async_client, mock_cache_service, mock_settings, mock_validator_healthy
    ):
        """Test comprehensive health check with database failure."""
        # Mock failing database
        failing_db = AsyncMock()
        failing_db.execute_query.side_effect = Exception("Database connection failed")

        with (
            patch(
                "tripsage.api.routers.health.ApiKeyValidator"
            ) as mock_validator_class,
            patch(
                "tripsage.api.core.dependencies.get_database_service",
                return_value=failing_db,
            ),
            patch(
                "tripsage.api.core.dependencies.get_cache_service",
                return_value=mock_cache_service,
            ),
            patch(
                "tripsage.api.core.dependencies.get_settings",
                return_value=mock_settings,
            ),
        ):
            mock_validator_class.return_value.__aenter__.return_value = (
                mock_validator_healthy
            )
            mock_validator_class.return_value.__aexit__.return_value = None

            response = await async_client.get("/api/health")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            # Overall status should be degraded due to database failure
            assert data["status"] == "degraded"

            # Verify database component shows failure
            db_component = next(
                c for c in data["components"] if c["name"] == "database"
            )
            assert db_component["status"] == "unhealthy"
            assert "Database connection failed" in db_component["message"]

    async def test_liveness_check(self, async_client):
        """Test basic liveness check endpoint."""
        response = await async_client.get("/api/health/liveness")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["status"] == "alive"
        assert "timestamp" in data

    async def test_readiness_check_ready(
        self, async_client, mock_db_service, mock_cache_service
    ):
        """Test readiness check when all dependencies are ready."""
        with (
            patch(
                "tripsage.api.core.dependencies.get_database_service",
                return_value=mock_db_service,
            ),
            patch(
                "tripsage.api.core.dependencies.get_cache_service",
                return_value=mock_cache_service,
            ),
        ):
            response = await async_client.get("/api/health/readiness")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert data["ready"] is True
            assert data["checks"]["database"] is True
            assert data["checks"]["cache"] is True
            assert "timestamp" in data

    async def test_readiness_check_not_ready(self, async_client, mock_cache_service):
        """Test readiness check when database is not ready."""
        # Mock failing database
        failing_db = AsyncMock()
        failing_db.execute_query.side_effect = Exception("Database not ready")

        with (
            patch(
                "tripsage.api.core.dependencies.get_database_service",
                return_value=failing_db,
            ),
            patch(
                "tripsage.api.core.dependencies.get_cache_service",
                return_value=mock_cache_service,
            ),
        ):
            response = await async_client.get("/api/health/readiness")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert data["ready"] is False
            assert data["checks"]["database"] is False
            assert data["checks"]["cache"] is True
            assert "Database" in data["details"]["database"]

    async def test_readiness_check_timeout(self, async_client, mock_cache_service):
        """Test readiness check with database timeout."""
        # Mock slow database
        slow_db = AsyncMock()

        async def slow_query(*args, **kwargs):
            await asyncio.sleep(10)  # Longer than timeout
            return [{"health_check": 1}]

        slow_db.execute_query.side_effect = slow_query

        with (
            patch(
                "tripsage.api.core.dependencies.get_database_service",
                return_value=slow_db,
            ),
            patch(
                "tripsage.api.core.dependencies.get_cache_service",
                return_value=mock_cache_service,
            ),
        ):
            response = await async_client.get("/api/health/readiness")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert data["ready"] is False
            assert data["checks"]["database"] is False
            assert "Database check timed out" in data["details"]["database"]

    async def test_specific_service_health_check_healthy(
        self, async_client, mock_validator_healthy
    ):
        """Test checking health of a specific external service."""
        with patch(
            "tripsage.api.routers.health.ApiKeyValidator"
        ) as mock_validator_class:
            mock_validator_class.return_value.__aenter__.return_value = (
                mock_validator_healthy
            )
            mock_validator_class.return_value.__aexit__.return_value = None

            response = await async_client.get("/api/health/services/openai")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert data["service"] == "openai"
            assert data["status"] == "healthy"
            assert data["latency_ms"] == 150.0
            assert data["message"] == "OpenAI API is operational"

    async def test_specific_service_health_check_unhealthy(self, async_client):
        """Test checking health of an unhealthy service."""
        unhealthy_validator = AsyncMock()
        unhealthy_validator.check_service_health.return_value = ServiceHealthCheck(
            service=ServiceType.OPENAI,
            status=ServiceHealthStatus.UNHEALTHY,
            latency_ms=5000.0,
            message="OpenAI API is down",
        )

        with patch(
            "tripsage.api.routers.health.ApiKeyValidator"
        ) as mock_validator_class:
            mock_validator_class.return_value.__aenter__.return_value = (
                unhealthy_validator
            )
            mock_validator_class.return_value.__aexit__.return_value = None

            response = await async_client.get("/api/health/services/openai")

            # Should return 503 for unhealthy service
            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            data = response.json()

            assert data["service"] == "openai"
            assert data["status"] == "unhealthy"
            assert data["message"] == "OpenAI API is down"

    async def test_specific_service_health_check_error(self, async_client):
        """Test service health check with error."""
        error_validator = AsyncMock()
        error_validator.check_service_health.side_effect = Exception(
            "Service check failed"
        )

        with patch(
            "tripsage.api.routers.health.ApiKeyValidator"
        ) as mock_validator_class:
            mock_validator_class.return_value.__aenter__.return_value = error_validator
            mock_validator_class.return_value.__aexit__.return_value = None

            response = await async_client.get("/api/health/services/openai")

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            data = response.json()

            assert data["service"] == "openai"
            assert data["status"] == "unknown"
            assert "Service check failed" in data["message"]

    async def test_database_health_check_detailed(self, async_client, mock_db_service):
        """Test detailed database health check endpoint."""
        with patch(
            "tripsage.api.core.dependencies.get_database_service",
            return_value=mock_db_service,
        ):
            response = await async_client.get("/api/health/database")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert data["name"] == "database"
            assert data["status"] == "healthy"
            assert data["message"] == "Database is responsive"
            assert data["latency_ms"] is not None
            assert "pool_size" in data["details"]

    async def test_cache_health_check_detailed(self, async_client, mock_cache_service):
        """Test detailed cache health check endpoint."""
        with patch(
            "tripsage.api.core.dependencies.get_cache_service",
            return_value=mock_cache_service,
        ):
            response = await async_client.get("/api/health/cache")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert data["name"] == "cache"
            assert data["status"] == "healthy"
            assert data["message"] == "Cache is responsive"
            assert data["latency_ms"] is not None
            assert "used_memory" in data["details"]

    async def test_cache_health_check_no_cache(self, async_client):
        """Test cache health check when cache is not configured."""
        with patch(
            "tripsage.api.core.dependencies.get_cache_service", return_value=None
        ):
            response = await async_client.get("/api/health/cache")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert data["name"] == "cache"
            assert data["status"] == "healthy"
            assert "Cache not configured" in data["message"]

    def test_invalid_service_type(self, async_client):
        """Test service health check with invalid service type."""
        import asyncio

        async def run_test():
            response = await async_client.get("/api/health/services/invalid_service")
            return response

        response = asyncio.run(run_test())

        # Should return validation error
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_external_services_check_exception(
        self, async_client, mock_db_service, mock_cache_service, mock_settings
    ):
        """Test comprehensive health check when external services check fails."""
        with (
            patch(
                "tripsage.api.routers.health.ApiKeyValidator"
            ) as mock_validator_class,
            patch(
                "tripsage.api.core.dependencies.get_database_service",
                return_value=mock_db_service,
            ),
            patch(
                "tripsage.api.core.dependencies.get_cache_service",
                return_value=mock_cache_service,
            ),
            patch(
                "tripsage.api.core.dependencies.get_settings",
                return_value=mock_settings,
            ),
        ):
            # Make the validator constructor raise an exception
            mock_validator_class.side_effect = Exception(
                "Validator initialization failed"
            )

            response = await async_client.get("/api/health")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            # Overall status should be degraded due to external services failure
            assert data["status"] == "degraded"

            # Should still have basic components
            assert len(data["components"]) >= 3  # app, db, cache
            assert data["external_services"] == {}

    async def test_health_endpoints_no_authentication_required(self, async_client):
        """Test that health endpoints don't require authentication."""
        # Test basic health check
        response = await async_client.get("/api/health")
        assert response.status_code in [
            200,
            422,
            500,
        ]  # Might fail on dependencies but not auth

        # Test liveness check
        response = await async_client.get("/api/health/liveness")
        assert response.status_code == status.HTTP_200_OK

    async def test_health_check_performance(self, async_client):
        """Test that health checks respond quickly."""
        import time

        # Act
        start_time = time.time()
        response = await async_client.get(
            "/api/health/liveness"
        )  # Use liveness for perf test
        end_time = time.time()

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert (end_time - start_time) < 1.0  # Should respond within 1 second

class TestHealthModels:
    """Test health check data models."""

    def test_component_health_model(self):
        """Test ComponentHealth model."""
        component = ComponentHealth(
            name="test_component",
            status="healthy",
            latency_ms=150.5,
            message="Test component is working",
            details={"test": "data"},
        )

        assert component.name == "test_component"
        assert component.status == "healthy"
        assert component.latency_ms == 150.5
        assert component.message == "Test component is working"
        assert component.details == {"test": "data"}

    def test_system_health_model(self):
        """Test SystemHealth model."""
        component = ComponentHealth(
            name="test",
            status="healthy",
        )

        health = SystemHealth(
            status="healthy",
            environment="test",
            components=[component],
        )

        assert health.status == "healthy"
        assert health.environment == "test"
        assert health.version == "1.0.0"
        assert len(health.components) == 1
        assert isinstance(health.timestamp, datetime)

    def test_readiness_check_model(self):
        """Test ReadinessCheck model."""
        readiness = ReadinessCheck(
            ready=True,
            checks={"database": True, "cache": True},
            details={"database": "healthy"},
        )

        assert readiness.ready is True
        assert readiness.checks["database"] is True
        assert readiness.details["database"] == "healthy"
        assert isinstance(readiness.timestamp, datetime)

    def test_component_health_model_defaults(self):
        """Test ComponentHealth model with defaults."""
        component = ComponentHealth(
            name="minimal",
            status="healthy",
        )

        assert component.name == "minimal"
        assert component.status == "healthy"
        assert component.latency_ms is None
        assert component.message is None
        assert component.details == {}

    def test_system_health_model_defaults(self):
        """Test SystemHealth model with defaults."""
        health = SystemHealth(
            status="healthy",
            environment="test",
            components=[],
        )

        assert health.status == "healthy"
        assert health.environment == "test"
        assert health.version == "1.0.0"
        assert health.components == []
        assert health.external_services == {}
        assert isinstance(health.timestamp, datetime)
        # Check that timestamp is recent (within last minute)
        now = datetime.now(timezone.utc)
        assert (now - health.timestamp).total_seconds() < 60
