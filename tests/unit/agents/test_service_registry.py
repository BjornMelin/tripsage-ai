"""
Tests for the ServiceRegistry dependency injection system.

This module tests the ServiceRegistry class which provides centralized
dependency injection for all agents, tools, and orchestration nodes.
"""

from unittest.mock import MagicMock, patch

import pytest

from tripsage.agents.service_registry import ServiceRegistry


class TestServiceRegistry:
    """Tests for the ServiceRegistry class."""

    def test_initialization_empty(self):
        """Test ServiceRegistry initialization with no services."""
        registry = ServiceRegistry()

        # All services should be None by default
        assert registry.accommodation_service is None
        assert registry.auth_service is None
        assert registry.memory_service is None
        assert registry.database_service is None

    def test_initialization_with_services(self):
        """Test ServiceRegistry initialization with services."""
        mock_db = MagicMock()
        mock_memory = MagicMock()

        registry = ServiceRegistry(database_service=mock_db, memory_service=mock_memory)

        assert registry.database_service is mock_db
        assert registry.memory_service is mock_memory
        assert registry.accommodation_service is None

    def test_get_required_service_success(self):
        """Test getting a required service that exists."""
        mock_memory = MagicMock()
        registry = ServiceRegistry(memory_service=mock_memory)

        result = registry.get_required_service("memory_service")
        assert result is mock_memory

    def test_get_required_service_failure(self):
        """Test getting a required service that doesn't exist."""
        registry = ServiceRegistry()

        with pytest.raises(
            ValueError, match="Required service 'memory_service' is not initialized"
        ):
            registry.get_required_service("memory_service")

    def test_get_optional_service_success(self):
        """Test getting an optional service that exists."""
        mock_memory = MagicMock()
        registry = ServiceRegistry(memory_service=mock_memory)

        result = registry.get_optional_service("memory_service")
        assert result is mock_memory

    def test_get_optional_service_none(self):
        """Test getting an optional service that doesn't exist."""
        registry = ServiceRegistry()

        result = registry.get_optional_service("memory_service")
        assert result is None

    def test_get_service_invalid_name(self):
        """Test getting a service with invalid name."""
        registry = ServiceRegistry()

        with pytest.raises(
            ValueError, match="Required service 'invalid_service' is not initialized"
        ):
            registry.get_required_service("invalid_service")

    def test_get_service_compatibility(self):
        """Test get_service method (compatibility alias for get_optional_service)."""
        mock_db = MagicMock()
        registry = ServiceRegistry(database_service=mock_db)

        assert registry.get_service("database_service") is mock_db
        assert registry.get_service("memory_service") is None

    @pytest.mark.asyncio
    async def test_create_default_success(self):
        """Test creating a default ServiceRegistry with all services."""
        mock_db = MagicMock()

        # Mock all the service constructors to avoid actual instantiation
        with patch.multiple(
            "tripsage.agents.service_registry",
            CacheService=MagicMock(),
            WebSocketManager=MagicMock(),
            WebSocketBroadcaster=MagicMock(),
            KeyMonitoringService=MagicMock(),
            GoogleMapsService=MagicMock(),
            WeatherService=MagicMock(),
            TimeService=MagicMock(),
            GoogleCalendarService=MagicMock(),
            DocumentAnalyzer=MagicMock(),
            PlaywrightService=MagicMock(),
            WebCrawlService=MagicMock(),
            UserService=MagicMock(),
            KeyManagementService=MagicMock(),
            MemoryService=MagicMock(),
            ChatService=MagicMock(),
            FileProcessingService=MagicMock(),
            AccommodationService=MagicMock(),
            FlightService=MagicMock(),
            DestinationService=MagicMock(),
            ItineraryService=MagicMock(),
            TripService=MagicMock(),
        ):
            registry = await ServiceRegistry.create_default(mock_db)

            assert registry.database_service is mock_db
            assert registry.cache_service is not None
            assert registry.memory_service is not None
            assert registry.accommodation_service is not None


class TestServiceRegistryIntegration:
    """Integration tests for ServiceRegistry."""

    def test_service_dependency_chain(self):
        """Test that services can depend on each other through registry."""
        mock_db = MagicMock()
        mock_cache = MagicMock()
        mock_memory = MagicMock()

        # Mock accommodation service that depends on other services
        mock_accommodation = MagicMock()

        registry = ServiceRegistry(
            database_service=mock_db,
            cache_service=mock_cache,
            memory_service=mock_memory,
            accommodation_service=mock_accommodation,
        )

        # Test that all dependent services are available
        assert registry.get_required_service("database_service") is mock_db
        assert registry.get_required_service("cache_service") is mock_cache
        assert registry.get_required_service("memory_service") is mock_memory
        assert (
            registry.get_required_service("accommodation_service") is mock_accommodation
        )

    def test_partial_service_registry(self):
        """Test registry with only some services configured."""
        mock_db = MagicMock()

        registry = ServiceRegistry(database_service=mock_db)

        # Required service should work
        assert registry.get_required_service("database_service") is mock_db

        # Optional services should return None
        assert registry.get_optional_service("memory_service") is None
        assert registry.get_optional_service("accommodation_service") is None

        # Required missing service should raise error
        with pytest.raises(ValueError):
            registry.get_required_service("memory_service")
