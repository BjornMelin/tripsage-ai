"""Destination service for destination management operations.

This service consolidates destination-related business logic including destination
search, discovery, points of interest management, weather integration, and travel
advisory information. It provides clean abstractions over external services
while maintaining proper data relationships.
"""

import logging
from datetime import UTC, date, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import Field

from tripsage_core.exceptions import (
    CoreDatabaseError,
    CoreExternalAPIError,
    CoreResourceNotFoundError as NotFoundError,
    CoreServiceError as ServiceError,
)
from tripsage_core.models.base_core_model import TripSageModel


logger = logging.getLogger(__name__)


class DestinationCategory(str, Enum):
    """Destination category enumeration."""

    CITY = "city"
    BEACH = "beach"
    MOUNTAIN = "mountain"
    COUNTRYSIDE = "countryside"
    HISTORICAL = "historical"
    CULTURAL = "cultural"
    ADVENTURE = "adventure"
    RELAXATION = "relaxation"
    FOOD_AND_WINE = "food_and_wine"
    WILDLIFE = "wildlife"
    BUSINESS = "business"
    OTHER = "other"


class SafetyLevel(str, Enum):
    """Safety level enumeration."""

    VERY_SAFE = "very_safe"
    SAFE = "safe"
    MODERATE = "moderate"
    CAUTION = "caution"
    HIGH_RISK = "high_risk"


class ClimateType(str, Enum):
    """Climate type enumeration."""

    TROPICAL = "tropical"
    SUBTROPICAL = "subtropical"
    TEMPERATE = "temperate"
    CONTINENTAL = "continental"
    ARID = "arid"
    MEDITERRANEAN = "mediterranean"
    ARCTIC = "arctic"
    ALPINE = "alpine"


class DestinationImage(TripSageModel):
    """Destination image information."""

    url: str = Field(..., description="Image URL")
    caption: str | None = Field(None, description="Image caption")
    is_primary: bool = Field(
        default=False, description="Whether this is the primary image"
    )
    attribution: str | None = Field(None, description="Image attribution/source")
    width: int | None = Field(None, description="Image width in pixels")
    height: int | None = Field(None, description="Image height in pixels")


class PointOfInterest(TripSageModel):
    """Point of interest information."""

    id: str = Field(..., description="POI ID")
    name: str = Field(..., description="POI name")
    category: str = Field(..., description="POI category")
    description: str | None = Field(None, description="POI description")
    address: str | None = Field(None, description="POI address")
    latitude: float | None = Field(None, description="Latitude coordinate")
    longitude: float | None = Field(None, description="Longitude coordinate")
    rating: float | None = Field(None, ge=0, le=5, description="POI rating")
    review_count: int | None = Field(None, ge=0, description="Number of reviews")
    price_level: int | None = Field(None, ge=1, le=4, description="Price level (1-4)")
    opening_hours: dict[str, str] | None = Field(
        None, description="Opening hours by day"
    )
    images: list[DestinationImage] = Field(
        default_factory=list, description="POI images"
    )
    website: str | None = Field(None, description="POI website URL")
    phone: str | None = Field(None, description="POI phone number")
    popular_times: dict[str, list[int]] | None = Field(
        None, description="Popular visiting times"
    )


class DestinationWeather(TripSageModel):
    """Destination weather information."""

    season: str = Field(..., description="Current season")
    temperature_high_c: float = Field(
        ..., description="Average high temperature in Celsius"
    )
    temperature_low_c: float = Field(
        ..., description="Average low temperature in Celsius"
    )
    temperature_high_f: float | None = Field(
        None, description="Average high temperature in Fahrenheit"
    )
    temperature_low_f: float | None = Field(
        None, description="Average low temperature in Fahrenheit"
    )
    precipitation_mm: float = Field(..., description="Average precipitation in mm")
    humidity_percent: float = Field(
        ..., ge=0, le=100, description="Average humidity percentage"
    )
    conditions: str = Field(..., description="Typical weather conditions")
    climate_type: ClimateType = Field(..., description="Climate classification")
    best_months: list[str] = Field(
        default_factory=list, description="Best months to visit"
    )
    avoid_months: list[str] = Field(default_factory=list, description="Months to avoid")


class TravelAdvisory(TripSageModel):
    """Travel advisory information."""

    safety_level: SafetyLevel = Field(..., description="Overall safety level")
    advisory_text: str | None = Field(None, description="Advisory text")
    last_updated: datetime = Field(..., description="Last updated timestamp")
    restrictions: list[str] = Field(
        default_factory=list, description="Current travel restrictions"
    )
    health_requirements: list[str] = Field(
        default_factory=list, description="Health requirements"
    )
    embassy_info: dict[str, str] | None = Field(
        None, description="Embassy contact information"
    )


class DestinationSearchRequest(TripSageModel):
    """Request model for destination search."""

    query: str = Field(..., min_length=1, max_length=200, description="Search query")
    categories: list[DestinationCategory] | None = Field(
        None, description="Preferred categories"
    )
    min_safety_rating: float | None = Field(
        None, ge=0, le=5, description="Minimum safety rating"
    )
    max_safety_rating: float | None = Field(
        None, ge=0, le=5, description="Maximum safety rating"
    )
    travel_month: str | None = Field(
        None, description="Month of travel for weather filtering"
    )
    budget_range: dict[str, float] | None = Field(
        None, description="Budget range in USD"
    )
    continent: str | None = Field(None, description="Preferred continent")
    country: str | None = Field(None, description="Preferred country")
    climate_preference: ClimateType | None = Field(
        None, description="Preferred climate type"
    )
    limit: int = Field(default=10, ge=1, le=50, description="Maximum number of results")
    include_weather: bool = Field(
        default=True, description="Include weather information"
    )
    include_pois: bool = Field(default=True, description="Include points of interest")
    include_advisory: bool = Field(default=True, description="Include travel advisory")


class Destination(TripSageModel):
    """Comprehensive destination information."""

    id: str = Field(..., description="Destination ID")
    name: str = Field(..., description="Destination name")
    country: str = Field(..., description="Country")
    region: str | None = Field(None, description="Region/state/province")
    city: str | None = Field(None, description="City")
    description: str | None = Field(None, description="Brief description")
    long_description: str | None = Field(None, description="Detailed description")

    categories: list[DestinationCategory] = Field(
        default_factory=list, description="Destination categories"
    )

    # Geographic information
    latitude: float | None = Field(None, description="Latitude coordinate")
    longitude: float | None = Field(None, description="Longitude coordinate")
    timezone: str | None = Field(None, description="Timezone")

    # Cultural information
    currency: str | None = Field(None, description="Local currency code")
    languages: list[str] = Field(default_factory=list, description="Primary languages")

    # Media
    images: list[DestinationImage] = Field(
        default_factory=list, description="Destination images"
    )

    # Ratings and reviews
    rating: float | None = Field(None, ge=0, le=5, description="Overall rating")
    review_count: int | None = Field(None, ge=0, description="Number of reviews")
    safety_rating: float | None = Field(None, ge=0, le=5, description="Safety rating")

    # Travel information
    visa_requirements: str | None = Field(None, description="Visa requirements")
    local_transportation: str | None = Field(
        None, description="Local transportation options"
    )
    popular_activities: list[str] = Field(
        default_factory=list, description="Popular activities"
    )

    # Points of interest
    points_of_interest: list[PointOfInterest] = Field(
        default_factory=list, description="POIs"
    )

    # Weather and climate
    weather: DestinationWeather | None = Field(None, description="Weather information")
    best_time_to_visit: list[str] = Field(
        default_factory=list, description="Best months to visit"
    )

    # Travel advisory
    travel_advisory: TravelAdvisory | None = Field(None, description="Travel advisory")

    # Metadata
    source: str | None = Field(None, description="Data source")
    last_updated: datetime | None = Field(None, description="Last updated timestamp")

    # Search context
    relevance_score: float | None = Field(
        None, ge=0, le=1, description="Search relevance score"
    )


class DestinationSearchResponse(TripSageModel):
    """Destination search response model."""

    search_id: str = Field(..., description="Search ID")
    destinations: list[Destination] = Field(..., description="Search results")
    search_parameters: DestinationSearchRequest = Field(
        ..., description="Original search parameters"
    )

    total_results: int = Field(..., description="Total number of results")
    results_returned: int = Field(..., description="Number of results returned")

    search_duration_ms: int | None = Field(
        None, description="Search duration in milliseconds"
    )
    cached: bool = Field(default=False, description="Whether results were cached")


class SavedDestinationRequest(TripSageModel):
    """Request model for saving a destination."""

    destination_id: str = Field(..., description="Destination ID to save")
    trip_id: str | None = Field(None, description="Associated trip ID")
    notes: str | None = Field(None, description="User notes about the destination")
    priority: int = Field(
        default=3, ge=1, le=5, description="Priority (1=highest, 5=lowest)"
    )
    planned_visit_date: date | None = Field(None, description="Planned visit date")
    duration_days: int | None = Field(
        None, ge=1, description="Planned duration in days"
    )


class SavedDestination(TripSageModel):
    """Saved destination information."""

    id: str = Field(..., description="Saved destination ID")
    user_id: str = Field(..., description="User ID")
    trip_id: str | None = Field(None, description="Associated trip ID")
    destination: Destination = Field(..., description="Destination details")
    notes: str | None = Field(None, description="User notes")
    priority: int = Field(..., description="Priority")
    planned_visit_date: date | None = Field(None, description="Planned visit date")
    duration_days: int | None = Field(None, description="Planned duration")
    saved_at: datetime = Field(..., description="When destination was saved")


class DestinationRecommendationRequest(TripSageModel):
    """Request model for destination recommendations."""

    user_interests: list[str] = Field(..., description="User interests")
    travel_style: str | None = Field(None, description="Travel style preference")
    budget_range: dict[str, float] | None = Field(
        None, description="Budget range in USD"
    )
    travel_dates: list[date] | None = Field(None, description="Potential travel dates")
    trip_duration_days: int | None = Field(None, ge=1, description="Trip duration")
    group_size: int | None = Field(None, ge=1, description="Travel group size")
    accessibility_needs: list[str] | None = Field(
        None, description="Accessibility requirements"
    )
    previous_destinations: list[str] | None = Field(
        None, description="Previously visited destinations"
    )
    limit: int = Field(default=5, ge=1, le=20, description="Maximum recommendations")


class DestinationRecommendation(TripSageModel):
    """Destination recommendation with reasoning."""

    destination: Destination = Field(..., description="Recommended destination")
    match_score: float = Field(
        ..., ge=0, le=1, description="Recommendation match score"
    )
    reasons: list[str] = Field(..., description="Reasons for recommendation")
    best_for: list[str] = Field(
        default_factory=list, description="What this destination is best for"
    )
    estimated_cost: dict[str, float] | None = Field(None, description="Estimated costs")


class DestinationService:
    """Comprehensive destination service for search, discovery, and management.

    This service handles:
    - Destination search and discovery
    - Points of interest management
    - Weather and travel advisory integration
    - Saved destinations management
    - Personalized recommendations
    """

    def __init__(
        self,
        database_service=None,
        weather_service=None,
        cache_ttl: int = 3600,
    ):
        """Initialize the destination service.

        Args:
            database_service: Database service for persistence
            weather_service: Weather service for climate data
            cache_ttl: Cache TTL in seconds
        """
        # Import here to avoid circular imports
        if database_service is None:
            from tripsage_core.services.infrastructure import get_database_service

            database_service = get_database_service()

        if weather_service is None:
            try:
                from tripsage_core.services.external_apis.weather_service import (
                    WeatherService,
                )

                weather_service = WeatherService()
            except ImportError:
                logger.warning("Weather service not available")
                weather_service = None

        self.db = database_service
        self.external_service = None  # No external destination service available
        self.weather_service = weather_service
        self.cache_ttl = cache_ttl

        # In-memory cache for search results
        self._search_cache: dict[str, tuple] = {}
        self._destination_cache: dict[str, tuple] = {}

    async def search_destinations(
        self, search_request: DestinationSearchRequest
    ) -> DestinationSearchResponse:
        """Search for destinations based on criteria.

        Args:
            search_request: Destination search parameters

        Returns:
            Destination search results

        Raises:
            ValidationError: If search parameters are invalid
            ServiceError: If search fails
        """
        try:
            search_id = str(uuid4())
            start_time = datetime.now(UTC)

            # Check cache first
            cache_key = self._generate_search_cache_key(search_request)
            cached_result = self._get_cached_search(cache_key)

            if cached_result:
                logger.info(
                    "Returning cached destination search results",
                    extra={"search_id": search_id, "cache_key": cache_key},
                )

                return DestinationSearchResponse(
                    search_id=search_id,
                    destinations=cached_result["destinations"],
                    search_parameters=search_request,
                    total_results=len(cached_result["destinations"]),
                    results_returned=len(cached_result["destinations"]),
                    search_duration_ms=None,
                    cached=True,
                )

            # Perform search
            destinations = []

            # Use mock destinations (no external service available)
            destinations = await self._generate_mock_destinations(search_request)

            # Enrich with weather data if requested
            if search_request.include_weather:
                destinations = await self._enrich_with_weather(destinations)

            # Enrich with travel advisory if requested
            if search_request.include_advisory:
                destinations = await self._enrich_with_advisory(destinations)

            # Score and rank destinations
            scored_destinations = await self._score_destinations(
                destinations, search_request
            )

            # Cache results
            self._cache_search_results(cache_key, {"destinations": scored_destinations})

            # Store search in database
            await self._store_search_history(
                search_id, search_request, scored_destinations
            )

            search_duration = int(
                (datetime.now(UTC) - start_time).total_seconds() * 1000
            )

            logger.info(
                "Destination search completed",
                extra={
                    "search_id": search_id,
                    "destinations_count": len(scored_destinations),
                    "duration_ms": search_duration,
                },
            )

            return DestinationSearchResponse(
                search_id=search_id,
                destinations=scored_destinations,
                search_parameters=search_request,
                total_results=len(scored_destinations),
                results_returned=len(scored_destinations),
                search_duration_ms=search_duration,
                cached=False,
            )

        except Exception as e:
            logger.exception(
                "Destination search failed",
                extra={"error": str(e), "query": search_request.query},
            )
            raise ServiceError(f"Destination search failed: {e!s}") from e

    async def get_destination_details(
        self,
        destination_id: str,
        include_weather: bool = True,
        include_pois: bool = True,
        include_advisory: bool = True,
    ) -> Destination | None:
        """Get detailed information about a destination.

        Args:
            destination_id: Destination ID
            include_weather: Include weather information
            include_pois: Include points of interest
            include_advisory: Include travel advisory

        Returns:
            Destination details or None if not found
        """
        try:
            # Check cache first
            cache_key = f"dest_{destination_id}"
            cached_result = self._get_cached_destination(cache_key)

            if cached_result:
                destination = cached_result
            else:
                # Try to get from database
                destination_data = await self.db.get_destination(destination_id)  # type: ignore
                if destination_data:
                    destination = Destination(**destination_data)
                else:
                    return None

                # Cache the result
                self._cache_destination(cache_key, destination)

            # Enrich with additional data if requested
            if include_weather and not destination.weather:
                destination = await self._enrich_destination_with_weather(destination)

            if include_pois and not destination.points_of_interest:
                destination = await self._enrich_destination_with_pois(destination)

            if include_advisory and not destination.travel_advisory:
                destination = await self._enrich_destination_with_advisory(destination)

            return destination

        except Exception as e:
            logger.exception(
                "Failed to get destination details",
                extra={"destination_id": destination_id, "error": str(e)},
            )
            return None

    async def save_destination(
        self, user_id: str, save_request: SavedDestinationRequest
    ) -> SavedDestination:
        """Save a destination for a user.

        Args:
            user_id: User ID
            save_request: Save destination request

        Returns:
            Saved destination information

        Raises:
            NotFoundError: If destination not found
            ServiceError: If save fails
        """
        try:
            # Get destination details
            destination = await self.get_destination_details(
                save_request.destination_id
            )
            if not destination:
                raise NotFoundError("Destination not found")

            saved_id = str(uuid4())
            now = datetime.now(UTC)

            saved_destination = SavedDestination(
                id=saved_id,
                user_id=user_id,
                trip_id=save_request.trip_id,
                destination=destination,
                notes=save_request.notes,
                priority=save_request.priority,
                planned_visit_date=save_request.planned_visit_date,
                duration_days=save_request.duration_days,
                saved_at=now,
            )

            # Store in database
            await self._store_saved_destination(saved_destination)

            logger.info(
                "Destination saved successfully",
                extra={
                    "saved_id": saved_id,
                    "user_id": user_id,
                    "destination_id": save_request.destination_id,
                },
            )

            return saved_destination

        except NotFoundError:
            raise
        except Exception as e:
            logger.exception(
                "Failed to save destination",
                extra={
                    "user_id": user_id,
                    "destination_id": save_request.destination_id,
                    "error": str(e),
                },
            )
            raise ServiceError(f"Failed to save destination: {e!s}") from e

    async def get_saved_destinations(
        self, user_id: str, trip_id: str | None = None, limit: int = 50
    ) -> list[SavedDestination]:
        """Get saved destinations for a user.

        Args:
            user_id: User ID
            trip_id: Optional trip ID filter
            limit: Maximum number of destinations

        Returns:
            List of saved destinations
        """
        try:
            filters = {"user_id": user_id}
            if trip_id:
                filters["trip_id"] = trip_id

            results = await self.db.get_saved_destinations(filters, limit)  # type: ignore

            return [SavedDestination(**result) for result in results]

        except Exception as e:
            logger.exception(
                "Failed to get saved destinations",
                extra={"user_id": user_id, "error": str(e)},
            )
            return []

    async def get_destination_recommendations(
        self, user_id: str, recommendation_request: DestinationRecommendationRequest
    ) -> list[DestinationRecommendation]:
        """Get personalized destination recommendations.

        Args:
            user_id: User ID
            recommendation_request: Recommendation parameters

        Returns:
            List of destination recommendations
        """
        try:
            # Get user's travel history and preferences
            user_preferences = await self._get_user_travel_preferences(user_id)
            saved_destinations = await self.get_saved_destinations(user_id)

            # Generate recommendations based on interests and history
            recommendations = await self._generate_recommendations(
                user_preferences, saved_destinations, recommendation_request
            )

            logger.info(
                "Generated destination recommendations",
                extra={
                    "user_id": user_id,
                    "recommendations_count": len(recommendations),
                },
            )

            return recommendations

        except Exception as e:
            logger.exception(
                "Failed to generate recommendations",
                extra={"user_id": user_id, "error": str(e)},
            )
            return []

    async def _generate_mock_destinations(
        self, search_request: DestinationSearchRequest
    ) -> list[Destination]:
        """Generate mock destinations for testing."""
        # Generate mock destinations based on query
        mock_data = [
            {
                "name": "Paris",
                "country": "France",
                "categories": [DestinationCategory.CITY, DestinationCategory.CULTURAL],
                "description": "The City of Light, famous for art and cuisine",
                "rating": 4.7,
                "safety_rating": 4.2,
                "latitude": 48.8566,
                "longitude": 2.3522,
            },
            {
                "name": "Bali",
                "country": "Indonesia",
                "categories": [
                    DestinationCategory.BEACH,
                    DestinationCategory.RELAXATION,
                ],
                "description": "Tropical paradise with beaches and culture",
                "rating": 4.5,
                "safety_rating": 4.0,
                "latitude": -8.3405,
                "longitude": 115.0920,
            },
            {
                "name": "Tokyo",
                "country": "Japan",
                "categories": [DestinationCategory.CITY, DestinationCategory.CULTURAL],
                "description": "Vibrant metropolis blending tradition and modernity",
                "rating": 4.6,
                "safety_rating": 4.8,
                "latitude": 35.6762,
                "longitude": 139.6503,
            },
        ]

        return [
            Destination(
                id=str(uuid4()),
                name=data["name"],
                country=data["country"],
                region=None,
                city=None,
                description=data["description"],
                long_description=None,
                categories=data["categories"],
                latitude=data["latitude"],
                longitude=data["longitude"],
                timezone=None,
                currency=None,
                languages=[],
                images=[
                    DestinationImage(
                        url=(
                            f"https://example.com/"
                            f"{data['name'].lower().replace(' ', '_')}.jpg"
                        ),
                        caption=None,
                        is_primary=True,
                        attribution=None,
                        width=None,
                        height=None,
                    )
                ],
                rating=data["rating"],
                review_count=None,
                safety_rating=data["safety_rating"],
                visa_requirements=None,
                local_transportation=None,
                popular_activities=[],
                points_of_interest=[],
                weather=None,
                best_time_to_visit=[],
                travel_advisory=None,
                source="mock",
                last_updated=datetime.now(UTC),
                relevance_score=None,
            )
            for data in mock_data[: search_request.limit]
        ]

    async def _enrich_with_weather(
        self, destinations: list[Destination]
    ) -> list[Destination]:
        """Enrich destinations with weather information."""
        if not self.weather_service:
            return destinations

        for destination in destinations:
            if destination.latitude and destination.longitude:
                try:
                    weather_data = await self.weather_service.get_climate_info(  # type: ignore
                        destination.latitude, destination.longitude
                    )

                    if weather_data:
                        destination.weather = DestinationWeather(
                            season=weather_data.get("season", "Unknown"),
                            temperature_high_c=weather_data.get("temp_high_c", 0),
                            temperature_low_c=weather_data.get("temp_low_c", 0),
                            temperature_high_f=None,
                            temperature_low_f=None,
                            precipitation_mm=weather_data.get("precipitation", 0),
                            humidity_percent=weather_data.get("humidity", 0),
                            conditions=weather_data.get("conditions", "Unknown"),
                            climate_type=ClimateType(
                                weather_data.get("climate_type", "temperate")
                            ),
                            best_months=weather_data.get("best_months", []),
                        )
                except CoreExternalAPIError as e:
                    logger.warning(
                        "Failed to get weather for %s",
                        destination.name,
                        extra={"error": str(e)},
                    )

        return destinations

    async def _enrich_with_advisory(
        self, destinations: list[Destination]
    ) -> list[Destination]:
        """Enrich destinations with travel advisory information."""
        for destination in destinations:
            try:
                # Mock travel advisory data
                advisory = TravelAdvisory(
                    safety_level=SafetyLevel.SAFE,
                    advisory_text=(
                        f"Standard travel precautions for {destination.country}"
                    ),
                    last_updated=datetime.now(UTC),
                    restrictions=[],
                    health_requirements=["Valid passport required"],
                    embassy_info=None,
                )
                destination.travel_advisory = advisory
            except ServiceError as e:
                logger.warning(
                    "Failed to get advisory for %s",
                    destination.name,
                    extra={"error": str(e)},
                )

        return destinations

    async def _score_destinations(
        self, destinations: list[Destination], search_request: DestinationSearchRequest
    ) -> list[Destination]:
        """Score and rank destinations based on search criteria."""
        if not destinations:
            return destinations

        for destination in destinations:
            score = 0.0

            # Base relevance score
            query_lower = search_request.query.lower()
            if query_lower in destination.name.lower():
                score += 0.4
            elif query_lower in destination.country.lower():
                score += 0.3
            elif (
                destination.description
                and query_lower in destination.description.lower()
            ):
                score += 0.2

            # Category match score
            if search_request.categories:
                category_matches = len(
                    set(search_request.categories) & set(destination.categories)
                )
                if category_matches > 0:
                    score += 0.3 * (category_matches / len(search_request.categories))

            # Safety rating score
            if destination.safety_rating:
                if search_request.min_safety_rating:
                    if destination.safety_rating >= search_request.min_safety_rating:
                        score += 0.2
                else:
                    score += 0.1 * (destination.safety_rating / 5.0)

            # Overall rating score
            if destination.rating:
                score += 0.1 * (destination.rating / 5.0)

            destination.relevance_score = min(1.0, score)

        # Sort by relevance score (highest first)
        return sorted(destinations, key=lambda x: x.relevance_score or 0, reverse=True)

    async def _enrich_destination_with_weather(
        self, destination: Destination
    ) -> Destination:
        """Enrich a single destination with weather data."""
        if destination.latitude and destination.longitude and self.weather_service:
            try:
                weather_data = await self.weather_service.get_climate_info(  # type: ignore
                    destination.latitude, destination.longitude
                )

                if weather_data:
                    destination.weather = DestinationWeather(
                        season=weather_data.get("season", "Unknown"),
                        temperature_high_c=weather_data.get("temp_high_c", 0),
                        temperature_low_c=weather_data.get("temp_low_c", 0),
                        temperature_high_f=None,
                        temperature_low_f=None,
                        precipitation_mm=weather_data.get("precipitation", 0),
                        humidity_percent=weather_data.get("humidity", 0),
                        conditions=weather_data.get("conditions", "Unknown"),
                        climate_type=ClimateType(
                            weather_data.get("climate_type", "temperate")
                        ),
                        best_months=weather_data.get("best_months", []),
                    )
            except CoreExternalAPIError as e:
                logger.warning(
                    "Failed to get weather for %s",
                    destination.name,
                    extra={"error": str(e)},
                )

        return destination

    async def _enrich_destination_with_pois(
        self, destination: Destination
    ) -> Destination:
        """Enrich a destination with points of interest."""
        # Mock POI data
        mock_pois = [
            PointOfInterest(
                id=str(uuid4()),
                name=f"Famous Landmark in {destination.name}",
                category="attraction",
                description=f"Must-see landmark in {destination.name}",
                address=None,
                latitude=None,
                longitude=None,
                rating=4.5,
                review_count=None,
                price_level=None,
                opening_hours=None,
                images=[],
                website=None,
                phone=None,
                popular_times=None,
            ),
            PointOfInterest(
                id=str(uuid4()),
                name="Local Museum",
                category="museum",
                description=f"Cultural museum showcasing {destination.name} history",
                address=None,
                latitude=None,
                longitude=None,
                rating=4.2,
                review_count=None,
                price_level=None,
                opening_hours=None,
                images=[],
                website=None,
                phone=None,
                popular_times=None,
            ),
        ]

        destination.points_of_interest = mock_pois
        return destination

    async def _enrich_destination_with_advisory(
        self, destination: Destination
    ) -> Destination:
        """Enrich a destination with travel advisory information."""
        advisory = TravelAdvisory(
            safety_level=SafetyLevel.SAFE,
            advisory_text=f"Standard travel precautions for {destination.country}",
            last_updated=datetime.now(UTC),
            restrictions=[],
            health_requirements=["Valid passport required"],
            embassy_info=None,
        )
        destination.travel_advisory = advisory
        return destination

    async def _get_user_travel_preferences(self, user_id: str) -> dict[str, Any]:
        """Get user travel preferences from database or defaults."""
        try:
            prefs = await self.db.get_user_travel_preferences(user_id)  # type: ignore
            return prefs or {}
        except CoreDatabaseError:
            return {}

    async def _generate_recommendations(
        self,
        user_preferences: dict[str, Any],
        saved_destinations: list[SavedDestination],
        request: DestinationRecommendationRequest,
    ) -> list[DestinationRecommendation]:
        """Generate personalized destination recommendations."""
        # Mock recommendation algorithm
        mock_recommendations = [
            {
                "destination": Destination(
                    id=str(uuid4()),
                    name="Kyoto",
                    country="Japan",
                    region=None,
                    city=None,
                    description="Ancient capital with beautiful temples and gardens",
                    long_description=None,
                    categories=[
                        DestinationCategory.CULTURAL,
                        DestinationCategory.HISTORICAL,
                    ],
                    latitude=None,
                    longitude=None,
                    timezone=None,
                    currency=None,
                    languages=[],
                    images=[],
                    rating=4.8,
                    review_count=None,
                    safety_rating=None,
                    visa_requirements=None,
                    local_transportation=None,
                    popular_activities=[],
                    points_of_interest=[],
                    weather=None,
                    best_time_to_visit=[],
                    travel_advisory=None,
                    source="recommendation_engine",
                    last_updated=None,
                    relevance_score=None,
                ),
                "match_score": 0.92,
                "reasons": [
                    "Matches your interest in cultural experiences",
                    "High rating from similar users",
                ],
                "best_for": [
                    "Cultural experiences",
                    "Historical sites",
                    "Traditional architecture",
                ],
            },
            {
                "destination": Destination(
                    id=str(uuid4()),
                    name="Iceland",
                    country="Iceland",
                    region=None,
                    city=None,
                    description="Land of fire and ice with stunning natural landscapes",
                    long_description=None,
                    categories=[
                        DestinationCategory.ADVENTURE,
                        DestinationCategory.MOUNTAIN,
                    ],
                    latitude=None,
                    longitude=None,
                    timezone=None,
                    currency=None,
                    languages=[],
                    images=[],
                    rating=4.6,
                    review_count=None,
                    safety_rating=None,
                    visa_requirements=None,
                    local_transportation=None,
                    popular_activities=[],
                    points_of_interest=[],
                    weather=None,
                    best_time_to_visit=[],
                    travel_advisory=None,
                    source="recommendation_engine",
                    last_updated=None,
                    relevance_score=None,
                ),
                "match_score": 0.87,
                "reasons": [
                    "Perfect for adventure travel",
                    "Unique natural landscapes",
                ],
                "best_for": [
                    "Adventure activities",
                    "Natural phenomena",
                    "Photography",
                ],
            },
        ]

        return [
            DestinationRecommendation(
                destination=rec_data["destination"],
                match_score=rec_data["match_score"],
                reasons=rec_data["reasons"],
                best_for=rec_data["best_for"],
                estimated_cost=None,
            )
            for rec_data in mock_recommendations[: request.limit]
        ]

    def _generate_search_cache_key(
        self, search_request: DestinationSearchRequest
    ) -> str:
        """Generate cache key for search request."""
        import hashlib

        key_data = (
            f"{search_request.query}:{search_request.categories}:"
            f"{search_request.min_safety_rating}:{search_request.limit}"
        )

        return hashlib.sha256(key_data.encode()).hexdigest()[:16]

    def _get_cached_search(self, cache_key: str) -> dict[str, Any] | None:
        """Get cached search results if still valid."""
        if cache_key in self._search_cache:
            result, timestamp = self._search_cache[cache_key]
            import time

            if time.time() - timestamp < self.cache_ttl:
                return result
            del self._search_cache[cache_key]
        return None

    def _cache_search_results(self, cache_key: str, result: dict[str, Any]) -> None:
        """Cache search results."""
        import time

        self._search_cache[cache_key] = (result, time.time())

    def _get_cached_destination(self, cache_key: str) -> Destination | None:
        """Get cached destination if still valid."""
        if cache_key in self._destination_cache:
            result, timestamp = self._destination_cache[cache_key]
            import time

            if time.time() - timestamp < self.cache_ttl:
                return result
            del self._destination_cache[cache_key]
        return None

    def _cache_destination(self, cache_key: str, destination: Destination) -> None:
        """Cache destination details."""
        import time

        self._destination_cache[cache_key] = (destination, time.time())

    async def _store_search_history(
        self,
        search_id: str,
        search_request: DestinationSearchRequest,
        destinations: list[Destination],
    ) -> None:
        """Store search history in database."""
        try:
            search_data = {
                "id": search_id,
                "query": search_request.query,
                "categories": [cat.value for cat in search_request.categories]
                if search_request.categories
                else [],
                "destinations_count": len(destinations),
                "search_timestamp": datetime.now(UTC).isoformat(),
            }

            await self.db.store_destination_search(search_data)  # type: ignore

        except CoreDatabaseError as e:
            logger.warning(
                "Failed to store search history",
                extra={"search_id": search_id, "error": str(e)},
            )

    async def _store_destination(self, destination: Destination) -> None:
        """Store destination in database."""
        try:
            destination_data = destination.model_dump()
            destination_data["stored_at"] = datetime.now(UTC).isoformat()

            await self.db.store_destination(destination_data)  # type: ignore

        except CoreDatabaseError as e:
            logger.warning(
                "Failed to store destination",
                extra={"destination_id": destination.id, "error": str(e)},
            )

    async def _store_saved_destination(
        self, saved_destination: SavedDestination
    ) -> None:
        """Store saved destination in database."""
        try:
            saved_data = saved_destination.model_dump()
            saved_data["created_at"] = datetime.now(UTC).isoformat()

            await self.db.store_saved_destination(saved_data)  # type: ignore

        except Exception as e:
            logger.exception(
                "Failed to store saved destination",
                extra={"saved_id": saved_destination.id, "error": str(e)},
            )
            raise


# Dependency function for FastAPI
async def get_destination_service() -> DestinationService:
    """Get destination service instance for dependency injection.

    Returns:
        DestinationService instance
    """
    return DestinationService()
