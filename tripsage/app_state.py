"""Application service container and FastAPI state helpers.

This module replaces the legacy ServiceRegistry pattern with a lifespan-managed
set of singletons stored on ``FastAPI.app.state``. It centralises service
construction, provides typed accessors, and exposes startup/shutdown helpers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, TypeVar, cast

from fastapi import FastAPI

from tripsage_core.services.business.search_facade import SearchFacade
from tripsage_core.services.infrastructure.database_service import (
    close_database_service,
)
from tripsage_core.utils.logging_utils import get_logger


if TYPE_CHECKING:  # pragma: no cover - import only for type checking
    from tripsage.orchestration.graph import TripSageOrchestrator
    from tripsage.orchestration.memory_bridge import SessionMemoryBridge
    from tripsage_core.services.airbnb_mcp import AirbnbMCP
    from tripsage_core.services.business.accommodation_service import (
        AccommodationService,
    )
    from tripsage_core.services.business.activity_service import ActivityService
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
    from tripsage_core.services.business.unified_search_service import (
        UnifiedSearchService,
    )
    from tripsage_core.services.business.user_service import UserService
    from tripsage_core.services.configuration_service import ConfigurationService
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
    )


logger = get_logger(__name__)
ServiceT = TypeVar("ServiceT")


# pylint: disable=too-many-instance-attributes
@dataclass(slots=True)
class AppServiceContainer:
    """Typed container for application-wide service singletons."""

    # Business services
    accommodation_service: AccommodationService | None = None
    chat_service: ChatService | None = None
    activity_service: ActivityService | None = None
    destination_service: DestinationService | None = None
    file_processing_service: FileProcessingService | None = None
    flight_service: FlightService | None = None
    itinerary_service: ItineraryService | None = None
    api_key_service: ApiKeyService | None = None
    memory_service: MemoryService | None = None
    search_facade: SearchFacade | None = None
    trip_service: TripService | None = None
    user_service: UserService | None = None
    unified_search_service: UnifiedSearchService | None = None
    configuration_service: ConfigurationService | None = None

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

    # Orchestration lifecycle helpers
    checkpoint_service: Any | None = None
    memory_bridge: SessionMemoryBridge | None = None
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


async def initialise_app_state(
    app: FastAPI,
) -> tuple[AppServiceContainer, TripSageOrchestrator]:
    """Initialise application services and attach them to app.state."""
    # Localised imports to avoid heavy module initialisation at import time
    from tripsage.orchestration.memory_bridge import SessionMemoryBridge
    from tripsage_core.config import get_settings
    from tripsage_core.services.airbnb_mcp import AirbnbMCP
    from tripsage_core.services.business.accommodation_service import (
        AccommodationService,
    )
    from tripsage_core.services.business.activity_service import ActivityService
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
    from tripsage_core.services.business.unified_search_service import (
        UnifiedSearchService,
    )
    from tripsage_core.services.business.user_service import UserService
    from tripsage_core.services.external_apis import (
        DocumentAnalyzer,
        GoogleMapsService,
        WeatherService,
        WebCrawlService,
    )
    from tripsage_core.services.infrastructure import (
        CacheService,
        KeyMonitoringService,
    )
    from tripsage_core.services.infrastructure.database_service import (
        get_database_service,
    )

    settings = get_settings()

    # Infrastructure
    database_service = await get_database_service()
    db_concrete: DatabaseService = database_service
    cache_service = CacheService()
    await cache_service.connect()

    key_monitoring_service = KeyMonitoringService()

    # External services
    google_maps_service = GoogleMapsService()
    await google_maps_service.connect()

    weather_service = WeatherService()
    document_analyzer = DocumentAnalyzer()
    webcrawl_service = WebCrawlService()

    # Business services
    user_service = UserService(database_service)
    from tripsage_core.services.business.api_key_service import ApiKeyDatabaseProtocol

    api_key_service = ApiKeyService(
        db=cast(ApiKeyDatabaseProtocol, database_service),
        cache=cache_service,
        settings=settings,
    )
    from tripsage_core.services.infrastructure.database_operations_mixin import (
        DatabaseServiceProtocol,
    )

    memory_service = MemoryService(
        database_service=cast(DatabaseServiceProtocol, db_concrete)
    )
    await memory_service.connect()
    chat_service = ChatService(database_service=database_service)
    file_processing_service = FileProcessingService(
        database_service=database_service,
        ai_analysis_service=document_analyzer,
    )
    accommodation_service = AccommodationService(database_service=database_service)
    activity_service = ActivityService(
        google_maps_service=google_maps_service,
        cache_service=cache_service,
    )
    destination_service = DestinationService(
        database_service=database_service,
        weather_service=weather_service,
    )
    flight_service = FlightService(database_service=db_concrete)
    itinerary_service = ItineraryService(database_service=db_concrete)
    trip_service = TripService(
        database_service=db_concrete,
        user_service=user_service,
    )
    unified_search_service = UnifiedSearchService(
        cache_service=cache_service,
        destination_service=destination_service,
        activity_service=activity_service,
        flight_service=flight_service,
        accommodation_service=accommodation_service,
    )

    search_facade = SearchFacade(
        destination_service=destination_service,
        activity_service=activity_service,
        unified_search_service=unified_search_service,
    )

    # Orchestration helpers
    from tripsage.orchestration.checkpoint_service import SupabaseCheckpointService

    checkpoint_service = SupabaseCheckpointService()
    memory_bridge = SessionMemoryBridge(memory_service=memory_service)
    mcp_service = AirbnbMCP()
    await mcp_service.initialize()

    services = AppServiceContainer(
        accommodation_service=accommodation_service,
        chat_service=chat_service,
        activity_service=activity_service,
        destination_service=destination_service,
        file_processing_service=file_processing_service,
        flight_service=flight_service,
        itinerary_service=itinerary_service,
        memory_service=memory_service,
        search_facade=search_facade,
        trip_service=trip_service,
        unified_search_service=unified_search_service,
        user_service=user_service,
        database_service=database_service,
        cache_service=cache_service,
        key_monitoring_service=key_monitoring_service,
        checkpoint_service=checkpoint_service,
        memory_bridge=memory_bridge,
        mcp_service=mcp_service,
        webcrawl_service=webcrawl_service,
    )

    from tripsage.orchestration.graph import TripSageOrchestrator

    orchestrator = TripSageOrchestrator(services=services)

    # Attach to app.state for DI
    app.state.services = services
    app.state.cache_service = cache_service
    app.state.google_maps_service = google_maps_service
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
        "database_service",
        "api_key_service",
        "mcp_service",
        "orchestrator",
    ):
        if hasattr(app.state, attr):
            delattr(app.state, attr)
