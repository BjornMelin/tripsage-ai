"""Application service container and FastAPI state helpers.

This module replaces the legacy ServiceRegistry pattern with a lifespan-managed
set of singletons stored on ``FastAPI.app.state``. It centralises service
construction, provides typed accessors, and exposes startup/shutdown helpers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TypeVar, cast

from fastapi import FastAPI

from tripsage.orchestration.graph import TripSageOrchestrator
from tripsage.orchestration.memory_bridge import SessionMemoryBridge
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
from tripsage_core.services.infrastructure.database_service import (
    close_database_service,
    get_database_service,
)
from tripsage_core.utils.logging_utils import get_logger


logger = get_logger(__name__)
ServiceT = TypeVar("ServiceT")


@dataclass(slots=True)
class AppServiceContainer:
    """Typed container for application-wide service singletons."""

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

    # Orchestration lifecycle helpers
    checkpoint_service: Any | None = None
    memory_bridge: SessionMemoryBridge | None = None
    mcp_bridge: Any | None = None
    mcp_service: AirbnbMCP | None = None

    def get_required_service(
        self,
        service_name: str,
        *,
        expected_type: type[ServiceT] | None = None,
    ) -> ServiceT:
        """Return a required service, raising if missing or mismatched."""
        service = getattr(self, service_name, None)
        if service is None:
            raise ValueError(f"Required service '{service_name}' is not initialised")
        if expected_type is not None and not isinstance(service, expected_type):
            raise TypeError(
                f"Service '{service_name}' is not of expected type "
                f"{expected_type.__name__}"
            )
        return cast(ServiceT, service)

    def get_optional_service(
        self,
        service_name: str,
        *,
        expected_type: type[ServiceT] | None = None,
    ) -> ServiceT | None:
        """Return an optional service when present."""
        service = getattr(self, service_name, None)
        if service is None:
            return None
        if expected_type is not None and not isinstance(service, expected_type):
            raise TypeError(
                f"Service '{service_name}' is not of expected type "
                f"{expected_type.__name__}"
            )
        return cast(ServiceT, service)


async def initialise_app_state(app: FastAPI) -> tuple[AppServiceContainer, TripSageOrchestrator]:
    """Initialise application services and attach them to app.state."""

    settings = get_settings()

    # Infrastructure
    database_service = await get_database_service()
    cache_service = CacheService()
    await cache_service.connect()

    websocket_broadcaster = WebSocketBroadcaster()
    await websocket_broadcaster.start()

    websocket_manager = WebSocketManager()
    websocket_manager.broadcaster = websocket_broadcaster
    await websocket_manager.start()

    key_monitoring_service = KeyMonitoringService()

    # External services
    google_maps_service = GoogleMapsService()
    await google_maps_service.connect()

    weather_service = WeatherService()
    time_service = TimeService()
    calendar_service = GoogleCalendarService()
    document_analyzer = DocumentAnalyzer()
    playwright_service = PlaywrightService()
    webcrawl_service = WebCrawlService()

    # Business services
    user_service = UserService(database_service)
    api_key_service = ApiKeyService(
        db=database_service,
        cache=cache_service,
        settings=settings,
    )
    memory_service = MemoryService(database_service=database_service)
    await memory_service.connect()
    chat_service = ChatService(database_service=database_service)
    file_processing_service = FileProcessingService(
        database_service=database_service,
        ai_analysis_service=document_analyzer,
    )
    accommodation_service = AccommodationService(database_service=database_service)
    destination_service = DestinationService(
        database_service=database_service,
        weather_service=weather_service,
    )
    flight_service = FlightService(database_service=database_service)
    itinerary_service = ItineraryService(database_service=database_service)
    trip_service = TripService(
        database_service=database_service,
        user_service=user_service,
    )

    # Orchestration helpers
    from tripsage.orchestration.checkpoint_service import SupabaseCheckpointService
    from tripsage.orchestration.mcp_bridge import AirbnbMCPBridge

    checkpoint_service = SupabaseCheckpointService()
    memory_bridge = SessionMemoryBridge(memory_service=memory_service)
    mcp_service = AirbnbMCP()
    await mcp_service.initialize()

    mcp_bridge = AirbnbMCPBridge(mcp_service=mcp_service)
    await mcp_bridge.initialize()

    services = AppServiceContainer(
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
        calendar_service=calendar_service,
        document_analyzer=document_analyzer,
        google_maps_service=google_maps_service,
        playwright_service=playwright_service,
        time_service=time_service,
        weather_service=weather_service,
        webcrawl_service=webcrawl_service,
        cache_service=cache_service,
        database_service=database_service,
        key_monitoring_service=key_monitoring_service,
        websocket_broadcaster=websocket_broadcaster,
        websocket_manager=websocket_manager,
        checkpoint_service=checkpoint_service,
        memory_bridge=memory_bridge,
        mcp_bridge=mcp_bridge,
        mcp_service=mcp_service,
    )

    orchestrator = TripSageOrchestrator(services=services)

    # Attach to app.state for DI
    app.state.services = services
    app.state.cache_service = cache_service
    app.state.google_maps_service = google_maps_service
    app.state.websocket_broadcaster = websocket_broadcaster
    app.state.websocket_manager = websocket_manager
    app.state.database_service = database_service
    app.state.api_key_service = api_key_service
    app.state.mcp_service = mcp_service
    app.state.orchestrator = orchestrator

    return services, orchestrator


async def shutdown_app_state(app: FastAPI) -> None:
    """Clean up application services stored on app.state."""

    services: AppServiceContainer | None = getattr(app.state, "services", None)

    if services is None:
        logger.warning("App services not initialised; skipping shutdown")
        return

    if services.websocket_manager:
        await services.websocket_manager.stop()
    if services.websocket_broadcaster:
        await services.websocket_broadcaster.stop()

    if services.cache_service:
        await services.cache_service.disconnect()
    if services.google_maps_service:
        await services.google_maps_service.close()
    if services.memory_service:
        await services.memory_service.close()
    if services.mcp_service:
        await services.mcp_service.shutdown()

    await close_database_service()

    # Clear references to avoid reuse after shutdown
    for attr in (
        "services",
        "cache_service",
        "google_maps_service",
        "websocket_broadcaster",
        "websocket_manager",
        "database_service",
        "api_key_service",
        "mcp_service",
        "orchestrator",
    ):
        if hasattr(app.state, attr):
            delattr(app.state, attr)
