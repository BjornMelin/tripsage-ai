"""Activity service for TripSage.

This service handles activity-related operations including searching for activities,
saving user activity selections, and managing activity data using Google Maps Places API
and web crawling for additional information.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Any

from tripsage.api.schemas.requests.activities import (
    ActivitySearchRequest,
)
from tripsage.api.schemas.responses.activities import (
    ActivityCoordinates,
    ActivityResponse,
    ActivitySearchResponse,
)
from tripsage.tools.web_tools import CachedWebSearchTool
from tripsage_core.exceptions.exceptions import CoreServiceError
from tripsage_core.services.external_apis.google_maps_service import (
    GoogleMapsService,
    GoogleMapsServiceError,
    get_google_maps_service,
)
from tripsage_core.services.infrastructure.cache_service import get_cache_service
from tripsage_core.utils.cache_utils import cached
from tripsage_core.utils.content_utils import ContentType
from tripsage_core.utils.decorator_utils import with_error_handling
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
        google_maps_service: GoogleMapsService | None = None,
        cache_service=None,
    ):
        """Initialize activity service.

        Args:
            google_maps_service: Google Maps service instance
            cache_service: Cache service instance
        """
        self.google_maps_service = google_maps_service
        self.cache_service = cache_service
        self.web_search_tool = CachedWebSearchTool(namespace="activity-search")

    async def ensure_services(self) -> None:
        """Ensure all required services are initialized."""
        if not self.google_maps_service:
            self.google_maps_service = await get_google_maps_service()

        if not self.cache_service:
            self.cache_service = await get_cache_service()

    @with_error_handling()
    @cached(content_type=ContentType.SEMI_STATIC, ttl=3600)  # 1 hour cache
    async def search_activities(
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
        await self.ensure_services()

        try:
            logger.info(f"Searching activities for destination: {request.destination}")

            # First, geocode the destination to get coordinates
            geocode_results = await self.google_maps_service.geocode(
                request.destination
            )
            if not geocode_results:
                logger.warning(
                    f"No geocoding results for destination: {request.destination}"
                )
                return ActivitySearchResponse(
                    activities=[],
                    total=0,
                    skip=0,
                    limit=20,
                    search_id=str(uuid.uuid4()),
                    filters_applied={"destination": request.destination},
                )

            # Get the primary location
            location = geocode_results[0]["geometry"]["location"]
            lat, lng = location["lat"], location["lng"]
            search_location = (lat, lng)

            logger.debug(f"Geocoded {request.destination} to ({lat}, {lng})")

            # Determine place types based on requested categories
            place_types = self._get_place_types_for_categories(request.categories or [])

            # Set search radius (default 10km, max 50km for activities)
            search_radius = min(50000, 10000)  # 10km default, 50km max

            activities = []

            if place_types:
                # Search using specific place types
                for place_type in place_types:
                    try:
                        results = await self._search_places_by_type(
                            search_location, place_type, search_radius, request
                        )
                        activities.extend(results)
                    except Exception as e:
                        logger.warning(f"Failed to search for {place_type}: {e}")
                        continue
            else:
                # General activity search
                search_query = f"activities things to do in {request.destination}"
                try:
                    search_results = await self.google_maps_service.search_places(
                        query=search_query,
                        location=search_location,
                        radius=search_radius,
                    )

                    if search_results.get("results"):
                        batch_tasks = []
                        for place in search_results["results"][
                            :20
                        ]:  # Limit to 20 results
                            task = self._convert_place_to_activity(place, request)
                            batch_tasks.append(task)

                        if batch_tasks:
                            batch_results = await asyncio.gather(
                                *batch_tasks, return_exceptions=True
                            )
                            for result in batch_results:
                                if isinstance(result, ActivityResponse):
                                    activities.append(result)
                                elif isinstance(result, Exception):
                                    logger.warning(f"Failed to convert place: {result}")

                except Exception as e:
                    logger.error(f"General activity search failed: {e}")

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
                f"Found {len(page_activities)} activities for {request.destination}"
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
                cached=False,  # Set by caching decorator if from cache
            )

        except GoogleMapsServiceError as e:
            logger.error(f"Google Maps API error in activity search: {e}")
            raise CoreServiceError(
                f"Maps API error: {e}", service="ActivityService"
            ) from e
        except Exception as e:
            logger.error(f"Unexpected error in activity search: {e}")
            raise CoreServiceError(
                f"Activity search failed: {e}", service="ActivityService"
            ) from e

    async def _search_places_by_type(
        self,
        location: tuple,
        place_type: str,
        radius: int,
        request: ActivitySearchRequest,
    ) -> list[ActivityResponse]:
        """Search for places of a specific type."""
        try:
            # Use Places API nearby search
            search_results = await self.google_maps_service.search_places(
                query=f"{place_type} near {request.destination}",
                location=location,
                radius=radius,
            )

            activities = []
            if search_results.get("results"):
                batch_tasks = []
                for place in search_results["results"][:10]:  # Limit per type
                    task = self._convert_place_to_activity(place, request)
                    batch_tasks.append(task)

                if batch_tasks:
                    batch_results = await asyncio.gather(
                        *batch_tasks, return_exceptions=True
                    )
                    for result in batch_results:
                        if isinstance(result, ActivityResponse):
                            activities.append(result)

            return activities
        except Exception as e:
            logger.warning(f"Failed to search places by type {place_type}: {e}")
            return []

    async def _convert_place_to_activity(
        self, place: dict[str, Any], request: ActivitySearchRequest
    ) -> ActivityResponse:
        """Convert a Google Places result to an ActivityResponse."""
        try:
            place_id = place.get("place_id", "")
            name = place.get("name", "Unknown Activity")

            # Get location
            geometry = place.get("geometry", {})
            location_data = geometry.get("location", {})
            coordinates = None
            if location_data:
                coordinates = ActivityCoordinates(
                    lat=location_data.get("lat", 0.0),
                    lng=location_data.get("lng", 0.0),
                )

            # Determine activity type from place types
            place_types = place.get("types", [])
            activity_type = self._determine_activity_type(place_types)

            # Get rating and price level
            rating = float(place.get("rating", 0.0))
            price_level = place.get("price_level", 1)  # Google's 0-4 scale

            # Convert price level to estimated price
            price = self._estimate_price_from_level(price_level, activity_type)

            # Get photos for images
            images = []
            if place.get("photos"):
                # Note: In production, you'd need to generate photo URLs using the
                # Places API.For now, we'll leave this empty or use placeholder
                images = []

            # Get address
            vicinity = place.get("vicinity", "") or place.get("formatted_address", "")

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
            )

        except Exception as e:
            logger.warning(f"Failed to convert place to activity: {e}")
            raise e

    def _get_place_types_for_categories(self, categories: list[str]) -> list[str]:
        """Get Google Places types for activity categories."""
        place_types = []
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
        elif "tourist_attraction" in place_types:
            return "tour"
        elif "museum" in place_types:
            return "cultural"
        elif "park" in place_types:
            return "nature"
        else:
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
        if request.wheelchair_accessible is True:
            # Only include activities that are explicitly wheelchair accessible
            # Since we don't have this data from basic Places API, we'll be conservative
            filtered = [a for a in filtered if a.wheelchair_accessible is True]

        return filtered

    @with_error_handling()
    async def get_activity_details(self, activity_id: str) -> ActivityResponse | None:
        """Get detailed information about a specific activity.

        Args:
            activity_id: Activity ID

        Returns:
            Activity details or None if not found

        Raises:
            ActivityServiceError: If retrieval fails
        """
        await self.ensure_services()

        try:
            # Extract Google Maps place ID if applicable
            if activity_id.startswith("gmp_"):
                place_id = activity_id[4:]  # Remove "gmp_" prefix

                # Get detailed place information
                place_details = await self.google_maps_service.get_place_details(
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

                if place_details.get("result"):
                    place = place_details["result"]
                    # Convert to ActivityResponse with enhanced details
                    return await self._convert_detailed_place_to_activity(
                        place, activity_id
                    )

            # For non-Google Maps activities, this would query your database
            logger.warning(f"Activity details not found for ID: {activity_id}")
            return None

        except GoogleMapsServiceError as e:
            logger.error(f"Google Maps API error getting activity details: {e}")
            raise ActivityServiceError(f"Maps API error: {e}", e) from e
        except Exception as e:
            logger.error(f"Error getting activity details for {activity_id}: {e}")
            raise ActivityServiceError(f"Failed to get activity details: {e}", e) from e

    async def _convert_detailed_place_to_activity(
        self, place: dict[str, Any], activity_id: str
    ) -> ActivityResponse:
        """Convert detailed Google Places result to ActivityResponse."""
        name = place.get("name", "Unknown Activity")
        formatted_address = place.get("formatted_address", "")

        # Get coordinates
        geometry = place.get("geometry", {})
        location_data = geometry.get("location", {})
        coordinates = None
        if location_data:
            coordinates = ActivityCoordinates(
                lat=location_data.get("lat", 0.0),
                lng=location_data.get("lng", 0.0),
            )

        # Determine activity type
        place_types = place.get("types", [])
        activity_type = self._determine_activity_type(place_types)

        # Get rating and price
        rating = float(place.get("rating", 0.0))
        price_level = place.get("price_level", 1)
        price = self._estimate_price_from_level(price_level, activity_type)

        # Get duration
        duration = self._estimate_duration(activity_type, place_types)

        # Build description from reviews or use default
        description = f"Popular {activity_type}"
        reviews = place.get("reviews", [])
        if reviews:
            # Use the first review snippet as part of description
            first_review = reviews[0].get("text", "")
            if first_review and len(first_review) > 50:
                description = first_review[:200] + "..."

        # Get opening hours
        opening_hours = place.get("opening_hours", {})
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
        )


# Global service instance
_activity_service: ActivityService | None = None


async def get_activity_service() -> ActivityService:
    """Get the global activity service instance."""
    global _activity_service

    if _activity_service is None:
        _activity_service = ActivityService()
        await _activity_service.ensure_services()

    return _activity_service


async def close_activity_service() -> None:
    """Close the global activity service instance."""
    global _activity_service
    _activity_service = None
