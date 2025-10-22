"""Service registry for dependency injection in agents and orchestration.

This module provides a centralized registry for all business services used by agents,
tools, and orchestration nodes. It ensures proper initialization and lifecycle
management of services while enabling easy testing through dependency injection.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, TypeVar, cast

from tripsage_core.config import get_settings
from tripsage_core.services.airbnb_mcp import AirbnbMCP
from tripsage_core.services.business.accommodation_service import AccommodationService
from tripsage_core.services.business.api_key_service import ApiKeyService
from tripsage_core.services.business.chat_service import ChatService
from tripsage_core.services.business.destination_service import DestinationService
from tripsage_core.services.business.file_processing_service import (
    FileProcessingService,
)
from tripsage_core.services.business.flight_service import FlightService
from tripsage_core.services.business.itinerary_service import ItineraryService
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


if TYPE_CHECKING:
    from tripsage.orchestration.checkpoint_manager import SupabaseCheckpointManager
    from tripsage.orchestration.mcp_bridge import AirbnbMCPBridge
    from tripsage.orchestration.memory_bridge import SessionMemoryBridge


ServiceT = TypeVar("ServiceT")


@dataclass(slots=True)
# pylint: disable=too-many-instance-attributes
class ServiceRegistry:
    """Central registry for all services used in the application.

    This class provides a single point of access for all services, ensuring
    proper initialization and dependency injection throughout the application.
    """

    # Business services
    accommodation_service: AccommodationService | None = None
    chat_service: ChatService | None = None
    destination_service: DestinationService | None = None
    file_processing_service: FileProcessingService | None = None
    flight_service: FlightService | None = None
    itinerary_service: ItineraryService | None = None
    api_key_service: ApiKeyService | None = None
    memory_service: MemoryService | None = None
    trip_service: TripService | None = None
    user_service: UserService | None = None

    # External API services
    calendar_service: GoogleCalendarService | None = None
    document_analyzer: DocumentAnalyzer | None = None
    google_maps_service: GoogleMapsService | None = None
    playwright_service: PlaywrightService | None = None
    time_service: TimeService | None = None
    weather_service: WeatherService | None = None
    webcrawl_service: WebCrawlService | None = None

    # Infrastructure services
    cache_service: CacheService | None = None
    database_service: DatabaseService | None = None
    key_monitoring_service: KeyMonitoringService | None = None
    websocket_broadcaster: WebSocketBroadcaster | None = None
    websocket_manager: WebSocketManager | None = None

    # Orchestration lifecycle services
    checkpoint_manager: SupabaseCheckpointManager | None = None
    memory_bridge: SessionMemoryBridge | None = None
    mcp_bridge: AirbnbMCPBridge | None = None
    mcp_service: AirbnbMCP | None = None

    @classmethod
    async def create_default(cls, db_service: DatabaseService) -> ServiceRegistry:
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
        settings = get_settings()
        user_service = UserService(db_service)
        api_key_service = ApiKeyService(
            db=db_service, cache=cache_service, settings=settings
        )
        memory_service = MemoryService(database_service=db_service)
        await memory_service.connect()
        chat_service = ChatService(database_service=db_service)
        file_processing_service = FileProcessingService(
            database_service=db_service, ai_analysis_service=document_analyzer
        )

        accommodation_service = AccommodationService(database_service=db_service)

        destination_service = DestinationService(
            database_service=db_service, weather_service=weather_service
        )

        flight_service = FlightService(database_service=db_service)

        itinerary_service = ItineraryService(database_service=db_service)

        trip_service = TripService(
            database_service=db_service, user_service=user_service
        )

        from tripsage.orchestration.checkpoint_manager import (
            SupabaseCheckpointManager,
        )
        from tripsage.orchestration.mcp_bridge import AirbnbMCPBridge
        from tripsage.orchestration.memory_bridge import SessionMemoryBridge

        checkpoint_manager = SupabaseCheckpointManager()
        memory_bridge = SessionMemoryBridge(memory_service=memory_service)
        mcp_service = AirbnbMCP()
        mcp_bridge = AirbnbMCPBridge(mcp_service=mcp_service)
        await mcp_bridge.initialize()

        return cls(
            # Business services
            accommodation_service=accommodation_service,
            chat_service=chat_service,
            destination_service=destination_service,
            file_processing_service=file_processing_service,
            flight_service=flight_service,
            itinerary_service=itinerary_service,
            api_key_service=api_key_service,
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
            checkpoint_manager=checkpoint_manager,
            memory_bridge=memory_bridge,
            mcp_bridge=mcp_bridge,
            mcp_service=mcp_service,
        )

    def get_required_service(
        self,
        service_name: str,
        *,
        expected_type: type[ServiceT] | None = None,
    ) -> ServiceT:
        """Get a required service by name, raising an error if not found.

        Args:
            service_name: The name of the service attribute.
            expected_type: Optional concrete type that the service must satisfy.

        Returns:
            The service instance cast to ``expected_type`` when provided.

        Raises:
            ValueError: If the service is not initialized.
            TypeError: If the service does not match ``expected_type``.
        """
        service = getattr(self, service_name, None)
        if service is None:
            raise ValueError(f"Required service '{service_name}' is not initialized")
        if expected_type is not None and not isinstance(service, expected_type):
            raise TypeError(
                f"Service '{service_name}' is not of expected type"
                f" {expected_type.__name__}"
            )
        return cast(ServiceT, service)

    def get_checkpoint_manager(self) -> SupabaseCheckpointManager:
        """Return the shared checkpoint manager instance."""
        if self.checkpoint_manager is None:
            raise ValueError(
                "Checkpoint manager is not configured on the service registry."
            )
        return self.checkpoint_manager

    def get_memory_bridge(self) -> SessionMemoryBridge:
        """Return the session memory bridge."""
        if self.memory_bridge is None:
            raise ValueError("Memory bridge is not configured on the service registry.")
        return self.memory_bridge

    async def get_mcp_bridge(self) -> AirbnbMCPBridge:
        """Return the LangGraph MCP bridge, ensuring it is initialized."""
        if self.mcp_bridge is None:
            raise ValueError("MCP bridge is not configured on the service registry.")
        if not self.mcp_bridge.is_initialized:
            await self.mcp_bridge.initialize()
        return self.mcp_bridge

    def get_optional_service(
        self,
        service_name: str,
        *,
        expected_type: type[ServiceT] | None = None,
    ) -> ServiceT | None:
        """Get an optional service by name, returning ``None`` if not found.

        Args:
            service_name: The name of the service attribute.
            expected_type: Optional concrete type that the service must satisfy.

        Returns:
            The service instance (when present) cast to ``expected_type``.

        Raises:
            TypeError: If the service is present but does not match ``expected_type``.
        """
        service = getattr(self, service_name, None)
        if service is None:
            return None
        if expected_type is not None and not isinstance(service, expected_type):
            raise TypeError(
                f"Service '{service_name}' is not of expected type"
                f" {expected_type.__name__}"
            )
        return cast(ServiceT, service)
