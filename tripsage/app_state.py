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
from tripsage_core.services.infrastructure.supabase_client import (
    get_admin_client,
    get_public_client,
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
    from tripsage_core.services.infrastructure import CacheService, DatabaseService


logger = get_logger(__name__)
ServiceT = TypeVar("ServiceT")


# pylint: disable=too-many-instance-attributes
@dataclass(slots=True)
class AppServiceContainer:
    """Typed container for application-wide service singletons."""

    # Business services
    accommodation_service: AccommodationService | None = None
    # chat_service removed
    activity_service: ActivityService | None = None
    destination_service: DestinationService | None = None
    file_processing_service: FileProcessingService | None = None
    flight_service: FlightService | None = None
    itinerary_service: ItineraryService | None = None
    memory_service: MemoryService | None = None
    search_facade: SearchFacade | None = None
    trip_service: TripService | None = None
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

    # Supabase clients
    supabase_admin_client: Any | None = None
    supabase_public_client: Any | None = None

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


async def _setup_infrastructure_services() -> tuple[DatabaseService, CacheService]:
    """Initialise infrastructure-layer services."""
    from tripsage_core.services.infrastructure import (
        CacheService,
    )
    from tripsage_core.services.infrastructure.database_service import (
        get_database_service,
    )

    database_service = await get_database_service()
    cache_service = CacheService()
    await cache_service.connect()
    return (database_service, cache_service)


async def _setup_external_services() -> tuple[
    GoogleMapsService, DocumentAnalyzer, WeatherService, WebCrawlService
]:
    """Initialise external API clients."""
    from tripsage_core.services.external_apis import (
        DocumentAnalyzer,
        GoogleMapsService,
        WeatherService,
        WebCrawlService,
    )

    google_maps_service = GoogleMapsService()
    await google_maps_service.connect()

    weather_service = WeatherService()
    document_analyzer = DocumentAnalyzer()
    webcrawl_service = WebCrawlService()
    return google_maps_service, document_analyzer, weather_service, webcrawl_service


async def _setup_business_services(
    *,
    database_service: DatabaseService,
    cache_service: CacheService,
    document_analyzer: DocumentAnalyzer,
    weather_service: WeatherService,
    google_maps_service: GoogleMapsService,
    settings: Any,
) -> dict[str, Any]:
    """Initialise business-layer services."""
    from tripsage_core.services.business.accommodation_service import (
        AccommodationService,
    )
    from tripsage_core.services.business.activity_service import ActivityService
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
    from tripsage_core.services.infrastructure.db_ops_mixin import (
        DatabaseServiceProtocol,
    )

    memory_service = MemoryService(
        database_service=cast(DatabaseServiceProtocol, database_service)
    )
    await memory_service.connect()

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
    flight_service = FlightService(database_service=database_service)
    itinerary_service = ItineraryService(database_service=database_service)
    trip_service = TripService(
        database_service=database_service,
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

    return {
        "accommodation_service": accommodation_service,
        "activity_service": activity_service,
        "destination_service": destination_service,
        "file_processing_service": file_processing_service,
        "flight_service": flight_service,
        "itinerary_service": itinerary_service,
        "memory_service": memory_service,
        "search_facade": search_facade,
        "trip_service": trip_service,
        "unified_search_service": unified_search_service,
    }


async def _setup_orchestration_helpers(
    memory_service: MemoryService,
) -> dict[str, Any]:
    """Initialise orchestration helpers."""
    from tripsage.orchestration.checkpoint_service import SupabaseCheckpointService
    from tripsage.orchestration.memory_bridge import SessionMemoryBridge
    from tripsage_core.services.airbnb_mcp import AirbnbMCP

    checkpoint_service = SupabaseCheckpointService()
    memory_bridge = SessionMemoryBridge(memory_service=memory_service)
    mcp_service = AirbnbMCP()
    await mcp_service.initialize()
    return {
        "checkpoint_service": checkpoint_service,
        "memory_bridge": memory_bridge,
        "mcp_service": mcp_service,
    }


def _build_service_container(
    *,
    business: dict[str, Any],
    infrastructure: tuple[DatabaseService, CacheService],
    external: tuple[
        GoogleMapsService, DocumentAnalyzer, WeatherService, WebCrawlService
    ],
    orchestration: dict[str, Any],
) -> AppServiceContainer:
    """Assemble the AppServiceContainer with the provided components."""
    database_service, cache_service = infrastructure
    (
        google_maps_service,
        document_analyzer,
        weather_service,
        webcrawl_service,
    ) = external

    return AppServiceContainer(
        accommodation_service=business["accommodation_service"],
        activity_service=business["activity_service"],
        destination_service=business["destination_service"],
        file_processing_service=business["file_processing_service"],
        flight_service=business["flight_service"],
        itinerary_service=business["itinerary_service"],
        memory_service=business["memory_service"],
        search_facade=business["search_facade"],
        trip_service=business["trip_service"],
        unified_search_service=business["unified_search_service"],
        calendar_service=None,
        document_analyzer=document_analyzer,
        google_maps_service=google_maps_service,
        weather_service=weather_service,
        webcrawl_service=webcrawl_service,
        cache_service=cache_service,
        database_service=database_service,
        checkpoint_service=orchestration["checkpoint_service"],
        memory_bridge=orchestration["memory_bridge"],
        mcp_service=orchestration["mcp_service"],
    )


def _attach_services_to_app_state(
    *,
    app: FastAPI,
    services: AppServiceContainer,
    database_service: DatabaseService,
    cache_service: CacheService,
    google_maps_service: GoogleMapsService,
    mcp_service: AirbnbMCP,
    orchestrator: TripSageOrchestrator,
) -> None:
    """Attach commonly accessed services to ``app.state``."""
    app.state.services = services
    app.state.cache_service = cache_service
    app.state.google_maps_service = google_maps_service
    app.state.database_service = database_service
    app.state.mcp_service = mcp_service
    app.state.orchestrator = orchestrator
    app.state.supabase_admin_client = services.supabase_admin_client
    app.state.supabase_public_client = services.supabase_public_client


async def initialise_app_state(
    app: FastAPI,
) -> tuple[AppServiceContainer, TripSageOrchestrator]:
    """Initialise application services and attach them to app.state."""
    from tripsage.orchestration.graph import TripSageOrchestrator
    from tripsage_core.config import get_settings

    settings = get_settings()

    infrastructure = await _setup_infrastructure_services()
    external = await _setup_external_services()
    business = await _setup_business_services(
        database_service=infrastructure[0],
        cache_service=infrastructure[1],
        document_analyzer=external[1],
        weather_service=external[2],
        google_maps_service=external[0],
        settings=settings,
    )
    orchestration = await _setup_orchestration_helpers(
        memory_service=business["memory_service"]
    )

    services = _build_service_container(
        business=business,
        infrastructure=infrastructure,
        external=external,
        orchestration=orchestration,
    )

    # Warm Supabase clients so downstream dependencies can reuse cached instances
    services.supabase_admin_client = await get_admin_client()
    services.supabase_public_client = await get_public_client()

    orchestrator = TripSageOrchestrator(services=services)

    _attach_services_to_app_state(
        app=app,
        services=services,
        database_service=infrastructure[0],
        cache_service=infrastructure[1],
        google_maps_service=external[0],
        mcp_service=orchestration["mcp_service"],
        orchestrator=orchestrator,
    )

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
        "mcp_service",
        "orchestrator",
    ):
        if hasattr(app.state, attr):
            delattr(app.state, attr)
