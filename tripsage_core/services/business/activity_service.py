"""Activity service for TripSage.

This service handles activity-related operations including searching for activities,
saving user activity selections, and managing activity data using Google Maps Places API
and web crawling for additional information.
"""

import asyncio
import uuid
from datetime import datetime

from tripsage.api.schemas.activities import (
    ActivityCoordinates,
    ActivityResponse,
    ActivitySearchRequest,
    ActivitySearchResponse,
)
from tripsage_core.exceptions.exceptions import CoreServiceError
from tripsage_core.models.api.maps_models import PlaceDetails, PlaceSummary
from tripsage_core.services.external_apis.google_maps_service import (
    GoogleMapsService,
    GoogleMapsServiceError,
)
from tripsage_core.services.infrastructure.cache_service import CacheService
from tripsage_core.utils.cache_utils import cached
from tripsage_core.utils.content_utils import ContentType
from tripsage_core.utils.error_handling_utils import tripsage_safe_execute
from tripsage_core.utils.logging_utils import get_logger


logger = get_logger(__name__)

# Activity type mappings for Google Places API
ACTIVITY_TYPE_MAPPING = {
    "adventure": ["amusement_park", "tourist_attraction"],
    "cultural": ["museum", "art_gallery", "cultural_center"],
    "entertainment": ["movie_theater", "bowling_alley", "night_club"],
    "food": ["restaurant", "cafe", "bar"],
    "nature": ["park", "zoo", "aquarium"],
    "religious": ["church", "hindu_temple", "mosque", "synagogue"],
    "shopping": ["shopping_mall", "store"],
    "sports": ["gym", "stadium", "sports_complex"],
    "tour": ["tourist_attraction", "travel_agency"],
    "wellness": ["spa", "beauty_salon", "gym"],
}


class ActivityServiceError(CoreServiceError):
    """Exception raised for activity service errors."""

    def __init__(self, message: str, original_error: Exception | None = None):
        """Construct the error with optional original exception."""
        super().__init__(
            message=message,
            code="ACTIVITY_SERVICE_ERROR",
            service="ActivityService",
            details={"original_error": str(original_error) if original_error else None},
        )
        self.original_error = original_error


class ActivityService:
    """Service for managing activity operations."""

    def __init__(
        self,
        google_maps_service: GoogleMapsService,
        cache_service: CacheService,
    ):
        """Initialize activity service.

        Args:
            google_maps_service: Google Maps service instance
            cache_service: Cache service instance
        """
        self.google_maps_service = google_maps_service
        self.cache_service = cache_service

    @tripsage_safe_execute()
    @cached(content_type=ContentType.SEMI_STATIC, ttl=3600)  # 1 hour cache
    async def search_activities(  # pylint: disable=too-many-statements, too-many-nested-blocks
        self, request: ActivitySearchRequest
    ) -> ActivitySearchResponse:
        """Search for activities based on the provided criteria.

        Args:
            request: Activity search request

        Returns:
            Activity search response with found activities

        Raises:
            ActivityServiceError: If search fails
        """
        # GoogleMapsService and CacheService are injected via constructor (DI)

        try:
            logger.info("Searching activities for destination: %s", request.destination)

            # First, geocode the destination to get coordinates
            geocode_results = await self.google_maps_service.geocode(
                request.destination
            )
            if not geocode_results:
                logger.warning(
                    "No geocoding results for destination: %s", request.destination
                )
                return ActivitySearchResponse(
                    activities=[],
                    total=0,
                    skip=0,
                    limit=20,
                    search_id=str(uuid.uuid4()),
                    filters_applied={"destination": request.destination},
                    cached=False,
                    provider_responses=None,
                )

            # Get the primary location (typed Place only)
            first_place = geocode_results[0]
            coords = first_place.coordinates
            if coords is None:
                logger.warning(
                    "Missing coordinates for destination: %s", request.destination
                )
                return ActivitySearchResponse(
                    activities=[],
                    total=0,
                    skip=0,
                    limit=20,
                    search_id=str(uuid.uuid4()),
                    filters_applied={"destination": request.destination},
                    cached=False,
                    provider_responses=None,
                )
            if coords.latitude is None or coords.longitude is None:
                logger.warning(
                    "Missing lat/lng for destination: %s", request.destination
                )
                return ActivitySearchResponse(
                    activities=[],
                    total=0,
                    skip=0,
                    limit=20,
                    search_id=str(uuid.uuid4()),
                    filters_applied={"destination": request.destination},
                    cached=False,
                    provider_responses=None,
                )
            lat_f = float(coords.latitude)
            lng_f = float(coords.longitude)
            search_location: tuple[float, float] = (lat_f, lng_f)

            logger.debug("Geocoded %s to (%s, %s)", request.destination, lat_f, lng_f)

            # Determine place types based on requested categories
            place_types = self._get_place_types_for_categories(request.categories or [])

            # Set search radius (default 10km, max 50km for activities)
            search_radius = 10000  # 10km

            activities: list[ActivityResponse] = []

            if place_types:
                activities = await self._search_activities_by_types(
                    search_location, place_types, search_radius, request
                )
            else:
                # General activity search
                search_query = f"activities things to do in {request.destination}"
                try:
                    search_results = await self.google_maps_service.search_places(
                        query=search_query,
                        location=search_location,
                        radius=search_radius,
                    )

                    if search_results:
                        batch_tasks = [
                            self._convert_place_summary_to_activity(summary, request)
                            for summary in search_results[:20]
                        ]  # Limit to 20 results

                        if batch_tasks:
                            batch_results = await asyncio.gather(
                                *batch_tasks, return_exceptions=True
                            )
                            activities.extend(
                                result
                                for result in batch_results
                                if isinstance(result, ActivityResponse)
                            )
                            for error in (
                                result
                                for result in batch_results
                                if isinstance(result, Exception)
                            ):
                                logger.warning("Failed to convert place: %s", error)

                except GoogleMapsServiceError as e:
                    logger.warning("General activity search failed: %s", e)

            # Apply additional filters
            filtered_activities = self._apply_filters(activities, request)

            # Sort by rating and distance
            sorted_activities = sorted(
                filtered_activities,
                key=lambda x: (x.rating, -float(x.price) if x.price > 0 else 0),
                reverse=True,
            )

            # Limit results
            total = len(sorted_activities)
            start_idx = 0  # request.skip if hasattr(request, 'skip') else 0
            end_idx = min(
                start_idx + 20, total
            )  # request.limit if hasattr(request, 'limit') else 20
            page_activities = sorted_activities[start_idx:end_idx]

            search_id = str(uuid.uuid4())
            logger.info(
                "Found %s activities for %s", len(page_activities), request.destination
            )

            return ActivitySearchResponse(
                activities=page_activities,
                total=total,
                skip=start_idx,
                limit=20,
                search_id=search_id,
                filters_applied={
                    "destination": request.destination,
                    "categories": request.categories,
                    "rating": request.rating,
                    "price_range": request.price_range.model_dump()
                    if request.price_range
                    else None,
                },
                cached=False,
                provider_responses=None,
            )

        except GoogleMapsServiceError as e:
            logger.exception("Google Maps API error in activity search")
            raise CoreServiceError(
                f"Maps API error: {e}", service="ActivityService"
            ) from e
        except Exception as e:
            logger.exception("Unexpected error in activity search")
            raise CoreServiceError(
                f"Activity search failed: {e}", service="ActivityService"
            ) from e

    async def _search_places_by_type(
        self,
        location: tuple[float, float],
        place_type: str,
        radius: int,
        request: ActivitySearchRequest,
    ) -> list[ActivityResponse]:
        """Search for places of a specific type."""
        # google_maps_service is injected and required

        try:
            # Use Places API nearby search
            search_results = await self.google_maps_service.search_places(
                query=f"{place_type} near {request.destination}",
                location=location,
                radius=radius,
            )

            if search_results:
                batch_tasks = [
                    self._convert_place_summary_to_activity(summary, request)
                    for summary in search_results[:10]
                ]  # Limit per type

                if batch_tasks:
                    batch_results = await asyncio.gather(
                        *batch_tasks, return_exceptions=True
                    )
                    return [
                        result
                        for result in batch_results
                        if isinstance(result, ActivityResponse)
                    ]

            return []
        except GoogleMapsServiceError as e:
            logger.warning("Failed to search places by type %s: %s", place_type, e)
            return []

    async def _search_activities_by_types(
        self,
        search_location: tuple[float, float],
        place_types: list[str],
        search_radius: int,
        request: ActivitySearchRequest,
    ) -> list[ActivityResponse]:
        """Search activities for multiple place types."""
        activities: list[ActivityResponse] = []
        for place_type in place_types:
            try:
                results = await self._search_places_by_type(
                    search_location, place_type, search_radius, request
                )
                activities.extend(results)
            except GoogleMapsServiceError as e:
                logger.warning("Failed to search for %s: %s", place_type, e)
                continue
        return activities

    async def _convert_place_summary_to_activity(
        self, summary: PlaceSummary, request: ActivitySearchRequest
    ) -> ActivityResponse:
        """Convert a typed PlaceSummary to an ActivityResponse."""
        try:
            place_id = summary.place.place_id or ""
            name = summary.place.name or "Unknown Activity"

            # Coordinates
            coordinates = None
            if (
                summary.place.coordinates
                and summary.place.coordinates.latitude is not None
                and summary.place.coordinates.longitude is not None
            ):
                coordinates = ActivityCoordinates(
                    lat=float(summary.place.coordinates.latitude),
                    lng=float(summary.place.coordinates.longitude),
                )

            # Determine activity type from place types
            place_types = summary.types or []
            activity_type = self._determine_activity_type(place_types)

            # Get rating and price level
            rating = float(summary.rating or 0.0)
            price_level = int(summary.price_level or 1)  # Google's 0-4 scale

            # Convert price level to estimated price
            price = self._estimate_price_from_level(price_level, activity_type)

            # Images can be resolved from PlaceDetails as needed
            images: list[str] = []

            # Get address
            vicinity: str = (
                summary.place.address.formatted
                if (
                    summary.place.address
                    and summary.place.address.formatted is not None
                )
                else ""
            )

            # Estimate duration based on activity type
            duration = self._estimate_duration(activity_type, place_types)

            # Create activity ID
            activity_id = (
                f"gmp_{place_id}" if place_id else f"act_{uuid.uuid4().hex[:8]}"
            )

            return ActivityResponse(
                id=activity_id,
                name=name,
                type=activity_type,
                location=vicinity,
                date=request.start_date.isoformat(),
                duration=duration,
                price=price,
                rating=rating,
                description=f"Popular {activity_type} in {request.destination}",
                images=images,
                coordinates=coordinates,
                provider="Google Maps",
                availability="Contact venue",
                wheelchair_accessible=None,  # Not available from basic Places API
                instant_confirmation=False,
                cancellation_policy=None,
                included=[],
                excluded=[],
                meeting_point=vicinity,
                languages=["English"],
                max_participants=None,
                min_participants=None,
            )

        except (ValueError, TypeError, KeyError) as e:
            logger.warning("Failed to convert place to activity: %s", e)
            raise

    def _get_place_types_for_categories(self, categories: list[str]) -> list[str]:
        """Get Google Places types for activity categories."""
        place_types: list[str] = []
        for category in categories:
            if category.lower() in ACTIVITY_TYPE_MAPPING:
                place_types.extend(ACTIVITY_TYPE_MAPPING[category.lower()])
        return list(set(place_types))  # Remove duplicates

    def _determine_activity_type(self, place_types: list[str]) -> str:
        """Determine activity type from Google Places types."""
        # Map Google Places types back to our activity categories
        for category, google_types in ACTIVITY_TYPE_MAPPING.items():
            if any(ptype in place_types for ptype in google_types):
                return category

        # Default categorization based on common types
        if "restaurant" in place_types or "food" in place_types:
            return "food"
        if "tourist_attraction" in place_types:
            return "tour"
        if "museum" in place_types:
            return "cultural"
        if "park" in place_types:
            return "nature"
        return "entertainment"

    def _estimate_price_from_level(self, price_level: int, activity_type: str) -> float:
        """Estimate price from Google's price level and activity type."""
        # Base prices by type (in USD)
        base_prices = {
            "adventure": 50.0,
            "cultural": 15.0,
            "entertainment": 25.0,
            "food": 20.0,
            "nature": 10.0,
            "religious": 0.0,
            "shopping": 30.0,
            "sports": 35.0,
            "tour": 40.0,
            "wellness": 60.0,
        }

        base_price = base_prices.get(activity_type, 25.0)

        # Multiply by price level
        # (0=free, 1=inexpensive, 2=moderate, 3=expensive, 4=very expensive)
        multipliers = [0.0, 1.0, 1.5, 2.5, 4.0]
        multiplier = multipliers[min(price_level, 4)]

        return base_price * multiplier

    def _estimate_duration(self, activity_type: str, place_types: list[str]) -> int:
        """Estimate duration in minutes based on activity type."""
        # Duration estimates by type (in minutes)
        durations = {
            "adventure": 240,  # 4 hours
            "cultural": 120,  # 2 hours
            "entertainment": 180,  # 3 hours
            "food": 90,  # 1.5 hours
            "nature": 180,  # 3 hours
            "religious": 60,  # 1 hour
            "shopping": 120,  # 2 hours
            "sports": 120,  # 2 hours
            "tour": 180,  # 3 hours
            "wellness": 90,  # 1.5 hours
        }

        return durations.get(activity_type, 120)  # Default 2 hours

    def _apply_filters(
        self, activities: list[ActivityResponse], request: ActivitySearchRequest
    ) -> list[ActivityResponse]:
        """Apply search filters to activities."""
        filtered = activities

        # Rating filter
        if request.rating is not None:
            filtered = [a for a in filtered if a.rating >= request.rating]

        # Price range filter
        if request.price_range:
            filtered = [
                a
                for a in filtered
                if request.price_range.min <= a.price <= request.price_range.max
            ]

        # Duration filter
        if request.duration:
            filtered = [a for a in filtered if a.duration <= request.duration]

        # Accessibility filter
        if request.wheelchair_accessible:
            logger.info(
                "Wheelchair accessibility filter requested but data not available "
                "from current API; including all activities"
            )

        return filtered

    @tripsage_safe_execute()
    async def get_activity_details(self, activity_id: str) -> ActivityResponse | None:
        """Get detailed information about a specific activity.

        Args:
            activity_id: Activity ID

        Returns:
            Activity details or None if not found

        Raises:
            ActivityServiceError: If retrieval fails
        """
        # Services injected via constructor; no lazy ensures

        try:
            # Extract Google Maps place ID if applicable
            if activity_id.startswith("gmp_"):
                place_id = activity_id[4:]  # Remove "gmp_" prefix

                # Get detailed place information
                assert self.google_maps_service is not None
                details = await self.google_maps_service.get_place_details(
                    place_id=place_id,
                    fields=[
                        "name",
                        "formatted_address",
                        "geometry",
                        "rating",
                        "price_level",
                        "types",
                        "opening_hours",
                        "photos",
                        "reviews",
                        "website",
                        "formatted_phone_number",
                    ],
                )

                return await self._convert_detailed_place_to_activity(
                    details, activity_id
                )

            # For non-Google Maps activities, this would query your database
            logger.warning("Activity details not found for ID: %s", activity_id)
            return None

        except GoogleMapsServiceError as e:
            logger.exception("Google Maps API error getting activity details")
            raise ActivityServiceError(f"Maps API error: {e}", e) from e
        except Exception as e:
            logger.exception("Error getting activity details for %s", activity_id)
            raise ActivityServiceError(f"Failed to get activity details: {e}", e) from e

    async def _convert_detailed_place_to_activity(
        self, details: PlaceDetails, activity_id: str
    ) -> ActivityResponse:
        """Convert typed PlaceDetails to ActivityResponse."""
        name = details.place.name or "Unknown Activity"
        formatted_address: str = (
            details.place.address.formatted
            if (details.place.address and details.place.address.formatted is not None)
            else ""
        )

        coordinates = None
        if (
            details.place.coordinates
            and details.place.coordinates.latitude is not None
            and details.place.coordinates.longitude is not None
        ):
            coordinates = ActivityCoordinates(
                lat=float(details.place.coordinates.latitude),
                lng=float(details.place.coordinates.longitude),
            )

        # Determine activity type
        place_types = details.types or []
        activity_type = self._determine_activity_type(place_types)

        # Get rating and price
        rating = float(details.rating or 0.0)
        price_level = int(details.price_level or 1)
        price = self._estimate_price_from_level(price_level, activity_type)

        # Get duration
        duration = self._estimate_duration(activity_type, place_types)

        # Build description from reviews or use default
        description = f"Popular {activity_type}"
        reviews = (details.raw or {}).get("reviews", [])
        if reviews:
            # Use the first review snippet as part of description
            first_review = reviews[0].get("text", "")
            if first_review and len(first_review) > 50:
                description = first_review[:200] + "..."

        # Get opening hours
        opening_hours = details.opening_hours or {}
        availability = "Contact venue"
        if opening_hours.get("open_now") is True:
            availability = "Open now"
        elif opening_hours.get("open_now") is False:
            availability = "Currently closed"

        return ActivityResponse(
            id=activity_id,
            name=name,
            type=activity_type,
            location=formatted_address,
            date=datetime.now().date().isoformat(),
            duration=duration,
            price=price,
            rating=rating,
            description=description,
            images=[],  # Would need to process photos
            coordinates=coordinates,
            provider="Google Maps",
            availability=availability,
            meeting_point=formatted_address,
            languages=["English"],  # Default
            wheelchair_accessible=None,
            instant_confirmation=False,
            cancellation_policy=None,
            included=[],
            excluded=[],
            max_participants=None,
            min_participants=None,
        )


"""Note: Use dependency injection. Construct ActivityService in a composition
root (e.g., FastAPI lifespan app.state container or API router) with injected
GoogleMapsService and CacheService. This module intentionally provides no
module-level singletons."""
