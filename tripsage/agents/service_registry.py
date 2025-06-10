"""Service registry for dependency injection in agents and orchestration.

This module provides a centralized registry for all business services used by agents,
tools, and orchestration nodes. It ensures proper initialization and lifecycle
management of services while enabling easy testing through dependency injection.
"""

from typing import Optional

from tripsage_core.services.business.accommodation_service import AccommodationService
from tripsage_core.services.business.auth_service import AuthenticationService
from tripsage_core.services.business.chat_service import ChatService
from tripsage_core.services.business.destination_service import DestinationService
from tripsage_core.services.business.file_processing_service import (
    FileProcessingService,
)
from tripsage_core.services.business.flight_service import FlightService
from tripsage_core.services.business.itinerary_service import ItineraryService
from tripsage_core.services.business.key_management_service import KeyManagementService
from tripsage_core.services.business.memory_service import MemoryService
from tripsage_core.services.business.trip_service import TripService
from tripsage_core.services.business.user_service import UserService
from tripsage_core.services.external_apis import (
    DocumentAnalyzer,
    GoogleCalendarService,
    GoogleMapsService,
    PlaywrightService,
    TimeService,
    WeatherService,
    WebCrawlService,
)
from tripsage_core.services.infrastructure import (
    CacheService,
    DatabaseService,
    KeyMonitoringService,
    WebSocketBroadcaster,
    WebSocketManager,
)


class ServiceRegistry:
    """Central registry for all services used in the application.

    This class provides a single point of access for all services, ensuring
    proper initialization and dependency injection throughout the application.
    """

    def __init__(
        self,
        # Business services
        accommodation_service: Optional[AccommodationService] = None,
        auth_service: Optional[AuthenticationService] = None,
        chat_service: Optional[ChatService] = None,
        destination_service: Optional[DestinationService] = None,
        file_processing_service: Optional[FileProcessingService] = None,
        flight_service: Optional[FlightService] = None,
        itinerary_service: Optional[ItineraryService] = None,
        key_management_service: Optional[KeyManagementService] = None,
        memory_service: Optional[MemoryService] = None,
        trip_service: Optional[TripService] = None,
        user_service: Optional[UserService] = None,
        # External API services
        calendar_service: Optional[GoogleCalendarService] = None,
        document_analyzer: Optional[DocumentAnalyzer] = None,
        google_maps_service: Optional[GoogleMapsService] = None,
        playwright_service: Optional[PlaywrightService] = None,
        time_service: Optional[TimeService] = None,
        weather_service: Optional[WeatherService] = None,
        webcrawl_service: Optional[WebCrawlService] = None,
        # Infrastructure services
        cache_service: Optional[CacheService] = None,
        database_service: Optional[DatabaseService] = None,
        key_monitoring_service: Optional[KeyMonitoringService] = None,
        websocket_broadcaster: Optional[WebSocketBroadcaster] = None,
        websocket_manager: Optional[WebSocketManager] = None,
    ):
        """Initialize the service registry with optional service instances.

        All services are optional to allow for partial initialization during testing
        or when only specific services are needed.
        """
        # Business services
        self.accommodation_service = accommodation_service
        self.auth_service = auth_service
        self.chat_service = chat_service
        self.destination_service = destination_service
        self.file_processing_service = file_processing_service
        self.flight_service = flight_service
        self.itinerary_service = itinerary_service
        self.key_management_service = key_management_service
        self.memory_service = memory_service
        self.trip_service = trip_service
        self.user_service = user_service

        # External API services
        self.calendar_service = calendar_service
        self.document_analyzer = document_analyzer
        self.google_maps_service = google_maps_service
        self.playwright_service = playwright_service
        self.time_service = time_service
        self.weather_service = weather_service
        self.webcrawl_service = webcrawl_service

        # Infrastructure services
        self.cache_service = cache_service
        self.database_service = database_service
        self.key_monitoring_service = key_monitoring_service
        self.websocket_broadcaster = websocket_broadcaster
        self.websocket_manager = websocket_manager

    @classmethod
    async def create_default(cls, db_service: DatabaseService) -> "ServiceRegistry":
        """Create a service registry with default service implementations.

        This factory method initializes all services with their default configurations
        and ensures proper dependency wiring between services.

        Args:
            db_service: The database service instance to use

        Returns:
            A fully initialized service registry
        """
        # Initialize infrastructure services first
        cache_service = CacheService()
        websocket_manager = WebSocketManager()
        websocket_broadcaster = WebSocketBroadcaster()
        key_monitoring_service = KeyMonitoringService()

        # Initialize external API services
        google_maps_service = GoogleMapsService()
        weather_service = WeatherService()
        time_service = TimeService()
        calendar_service = GoogleCalendarService()
        document_analyzer = DocumentAnalyzer()
        playwright_service = PlaywrightService()
        webcrawl_service = WebCrawlService()

        # Initialize business services with dependencies
        user_service = UserService(db_service)
        auth_service = AuthenticationService(db_service, user_service)
        key_management_service = KeyManagementService(db_service)
        memory_service = MemoryService(db_service)
        chat_service = ChatService(db_service, memory_service)
        file_processing_service = FileProcessingService(document_analyzer)

        accommodation_service = AccommodationService(
            db_service, cache_service, google_maps_service
        )

        destination_service = DestinationService(
            db_service, cache_service, google_maps_service, weather_service
        )

        flight_service = FlightService(db_service, cache_service)

        itinerary_service = ItineraryService(
            db_service, google_maps_service, weather_service
        )

        trip_service = TripService(db_service, memory_service, itinerary_service)

        return cls(
            # Business services
            accommodation_service=accommodation_service,
            auth_service=auth_service,
            chat_service=chat_service,
            destination_service=destination_service,
            file_processing_service=file_processing_service,
            flight_service=flight_service,
            itinerary_service=itinerary_service,
            key_management_service=key_management_service,
            memory_service=memory_service,
            trip_service=trip_service,
            user_service=user_service,
            # External API services
            calendar_service=calendar_service,
            document_analyzer=document_analyzer,
            google_maps_service=google_maps_service,
            playwright_service=playwright_service,
            time_service=time_service,
            weather_service=weather_service,
            webcrawl_service=webcrawl_service,
            # Infrastructure services
            cache_service=cache_service,
            database_service=db_service,
            key_monitoring_service=key_monitoring_service,
            websocket_broadcaster=websocket_broadcaster,
            websocket_manager=websocket_manager,
        )

    def get_required_service(self, service_name: str):
        """Get a required service by name, raising an error if not found.

        Args:
            service_name: The name of the service attribute

        Returns:
            The service instance

        Raises:
            ValueError: If the service is not initialized
        """
        service = getattr(self, service_name, None)
        if service is None:
            raise ValueError(f"Required service '{service_name}' is not initialized")
        return service

    def get_optional_service(self, service_name: str):
        """Get an optional service by name, returning None if not found.

        Args:
            service_name: The name of the service attribute

        Returns:
            The service instance or None
        """
        return getattr(self, service_name, None)

    def get_service(self, service_name: str):
        """Get a service by name, for compatibility with tests.

        Args:
            service_name: The name of the service attribute

        Returns:
            The service instance or None
        """
        return self.get_optional_service(service_name)
