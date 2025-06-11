"""Trip service for TripSage API.

This service acts as a thin wrapper around the core trip service,
handling API-specific concerns like model adaptation and FastAPI integration.
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID, uuid4

from fastapi import Depends

from tripsage.api.schemas.requests.trips import CreateTripRequest, UpdateTripRequest
from tripsage.api.schemas.responses.trips import TripResponse
from tripsage_core.exceptions.exceptions import (
    CoreServiceError as ServiceError,
)
from tripsage_core.exceptions.exceptions import (
    CoreValidationError as ValidationError,
)
from tripsage_core.services.business.trip_service import (
    TripCreateRequest as CoreTripCreateRequest,
)
from tripsage_core.services.business.trip_service import (
    TripLocation,
)
from tripsage_core.services.business.trip_service import (
    TripService as CoreTripService,
)
from tripsage_core.services.business.trip_service import (
    get_trip_service as get_core_trip_service,
)

logger = logging.getLogger(__name__)


class TripService:
    """
    API trip service that delegates to core business services.

    This service acts as a façade, handling:
    - Model adaptation between API and core models
    - API-specific error handling
    - FastAPI dependency integration
    """

    def __init__(self, core_trip_service: Optional[CoreTripService] = None):
        """
        Initialize the API trip service.

        Args:
            core_trip_service: Core trip service
        """
        self.core_trip_service = core_trip_service

    async def _get_core_trip_service(self) -> CoreTripService:
        """Get or create core trip service instance."""
        if self.core_trip_service is None:
            self.core_trip_service = await get_core_trip_service()
        return self.core_trip_service

    async def create_trip(
        self, user_id: str, request: CreateTripRequest
    ) -> TripResponse:
        """Create a new trip.

        Args:
            user_id: User ID
            request: Trip creation request

        Returns:
            Created trip response

        Raises:
            ValidationError: If request data is invalid
            ServiceError: If creation fails
        """
        try:
            logger.info(f"Creating trip for user: {user_id}")

            # Adapt API request to core model
            core_request = self._adapt_create_trip_request(request)

            # Create trip via core service
            core_service = await self._get_core_trip_service()
            core_response = await core_service.create_trip(user_id, core_request)

            # Adapt core response to API model
            return self._adapt_trip_response(core_response)

        except (ValidationError, ServiceError) as e:
            logger.error(f"Trip creation failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating trip: {str(e)}")
            raise ServiceError("Trip creation failed") from e

    async def get_trip(self, user_id: str, trip_id: UUID) -> Optional[TripResponse]:
        """Get a trip by ID.

        Args:
            user_id: User ID
            trip_id: Trip ID

        Returns:
            Trip response if found, None otherwise

        Raises:
            ServiceError: If retrieval fails
        """
        try:
            logger.info(f"Getting trip {trip_id} for user: {user_id}")

            # Get trip via core service
            core_service = await self._get_core_trip_service()
            core_response = await core_service.get_trip(user_id, str(trip_id))

            if core_response is None:
                return None

            # Adapt core response to API model
            return self._adapt_trip_response(core_response)

        except Exception as e:
            logger.error(f"Failed to get trip: {str(e)}")
            raise ServiceError("Failed to get trip") from e

    async def list_trips(
        self, user_id: str, limit: int = 50, offset: int = 0
    ) -> List[TripResponse]:
        """List trips for a user.

        Args:
            user_id: User ID
            limit: Maximum number of trips to return
            offset: Number of trips to skip

        Returns:
            List of trips

        Raises:
            ServiceError: If listing fails
        """
        try:
            logger.info(f"Listing trips for user: {user_id}")

            # List trips via core service
            core_service = await self._get_core_trip_service()
            core_trips = await core_service.list_trips(user_id, limit, offset)

            # Adapt core response to API model
            return [self._adapt_trip_response(trip) for trip in core_trips]

        except Exception as e:
            logger.error(f"Failed to list trips: {str(e)}")
            raise ServiceError("Failed to list trips") from e

    async def update_trip(
        self, user_id: str, trip_id: UUID, request: UpdateTripRequest
    ) -> Optional[TripResponse]:
        """Update a trip.

        Args:
            user_id: User ID
            trip_id: Trip ID
            request: Trip update request

        Returns:
            Updated trip if successful, None if trip not found

        Raises:
            ValidationError: If update data is invalid
            ServiceError: If update fails
        """
        try:
            logger.info(f"Updating trip {trip_id} for user: {user_id}")

            # Adapt API request to core model
            core_request = self._adapt_update_trip_request(request)

            # Update trip via core service
            core_service = await self._get_core_trip_service()
            core_response = await core_service.update_trip(
                user_id, str(trip_id), core_request
            )

            if core_response is None:
                return None

            # Adapt core response to API model
            return self._adapt_trip_response(core_response)

        except (ValidationError, ServiceError) as e:
            logger.error(f"Trip update failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error updating trip: {str(e)}")
            raise ServiceError("Trip update failed") from e

    async def delete_trip(self, user_id: str, trip_id: UUID) -> bool:
        """Delete a trip.

        Args:
            user_id: User ID
            trip_id: Trip ID

        Returns:
            True if deleted successfully

        Raises:
            ServiceError: If deletion fails
        """
        try:
            logger.info(f"Deleting trip {trip_id} for user: {user_id}")

            # Delete trip via core service
            core_service = await self._get_core_trip_service()
            return await core_service.delete_trip(user_id, str(trip_id))

        except Exception as e:
            logger.error(f"Failed to delete trip: {str(e)}")
            raise ServiceError("Failed to delete trip") from e

    async def get_trip_statistics(self, user_id: str, trip_id: UUID) -> dict:
        """Get statistics for a trip.

        Args:
            user_id: User ID
            trip_id: Trip ID

        Returns:
            Trip statistics

        Raises:
            ServiceError: If retrieval fails
        """
        try:
            logger.info(f"Getting statistics for trip {trip_id}")

            # Get statistics via core service
            core_service = await self._get_core_trip_service()
            return await core_service.get_trip_statistics(user_id, str(trip_id))

        except Exception as e:
            logger.error(f"Failed to get trip statistics: {str(e)}")
            raise ServiceError("Failed to get trip statistics") from e

    async def search_trips(
        self, user_id: str, query: str, limit: int = 20
    ) -> List[TripResponse]:
        """Search trips for a user.

        Args:
            user_id: User ID
            query: Search query
            limit: Maximum number of results

        Returns:
            List of matching trips

        Raises:
            ServiceError: If search fails
        """
        try:
            logger.info(f"Searching trips for user: {user_id}")

            # Search trips via core service
            core_service = await self._get_core_trip_service()
            core_trips = await core_service.search_trips(user_id, query, limit)

            # Adapt core response to API model
            return [self._adapt_trip_response(trip) for trip in core_trips]

        except Exception as e:
            logger.error(f"Failed to search trips: {str(e)}")
            raise ServiceError("Failed to search trips") from e

    async def get_trip_summary(self, user_id: str, trip_id: UUID) -> Optional[dict]:
        """Get trip summary.

        Args:
            user_id: User ID
            trip_id: Trip ID

        Returns:
            Trip summary data

        Raises:
            ServiceError: If retrieval fails
        """
        try:
            logger.info(f"Getting trip summary {trip_id} for user: {user_id}")

            # Get trip first to ensure access
            trip = await self.get_trip(user_id, trip_id)
            if not trip:
                return None

            # Build summary from trip data
            summary = {
                "id": str(trip_id),
                "title": trip.title,
                "date_range": f"{trip.start_date.strftime('%b %d')}-{trip.end_date.strftime('%d, %Y')}",
                "duration_days": trip.duration_days,
                "destinations": [dest.name for dest in trip.destinations],
                "accommodation_summary": "4-star hotels in city centers",  # TODO: Get from actual data
                "transportation_summary": "Economy flights, local transit",  # TODO: Get from actual data
                "budget_summary": {
                    "total": 5000,  # TODO: Get from trip preferences
                    "currency": "USD",
                    "spent": 1500,
                    "remaining": 3500,
                    "breakdown": {
                        "accommodation": {"budget": 2000, "spent": 800},
                        "transportation": {"budget": 1500, "spent": 700},
                        "food": {"budget": 1000, "spent": 0},
                        "activities": {"budget": 500, "spent": 0},
                    },
                },
                "has_itinerary": True,  # TODO: Check actual itinerary
                "completion_percentage": 75,  # TODO: Calculate actual percentage
            }

            return summary

        except Exception as e:
            logger.error(f"Failed to get trip summary: {str(e)}")
            raise ServiceError("Failed to get trip summary") from e

    async def update_trip_preferences(
        self, user_id: str, trip_id: UUID, preferences: dict
    ) -> Optional[TripResponse]:
        """Update trip preferences.

        Args:
            user_id: User ID
            trip_id: Trip ID
            preferences: Trip preferences

        Returns:
            Updated trip if successful, None if trip not found

        Raises:
            ServiceError: If update fails
        """
        try:
            logger.info(f"Updating trip preferences {trip_id} for user: {user_id}")

            # Create update request with preferences
            from tripsage.api.schemas.requests.trips import UpdateTripRequest

            update_request = UpdateTripRequest()
            # TODO: Map preferences to update request properly

            # Update via existing update method
            return await self.update_trip(user_id, trip_id, update_request)

        except Exception as e:
            logger.error(f"Failed to update trip preferences: {str(e)}")
            raise ServiceError("Failed to update trip preferences") from e

    async def duplicate_trip(
        self, user_id: str, trip_id: UUID
    ) -> Optional[TripResponse]:
        """Duplicate a trip.

        Args:
            user_id: User ID
            trip_id: Trip ID to duplicate

        Returns:
            Duplicated trip if successful, None if original trip not found

        Raises:
            ServiceError: If duplication fails
        """
        try:
            logger.info(f"Duplicating trip {trip_id} for user: {user_id}")

            # Get original trip
            original_trip = await self.get_trip(user_id, trip_id)
            if not original_trip:
                return None

            # Create new trip based on original
            from tripsage.api.schemas.requests.trips import CreateTripRequest

            duplicate_request = CreateTripRequest(
                title=f"Copy of {original_trip.title}",
                description=original_trip.description,
                start_date=original_trip.start_date,
                end_date=original_trip.end_date,
                destinations=original_trip.destinations,
                preferences=original_trip.preferences,
            )

            return await self.create_trip(user_id, duplicate_request)

        except Exception as e:
            logger.error(f"Failed to duplicate trip: {str(e)}")
            raise ServiceError("Failed to duplicate trip") from e

    async def get_trip_itinerary(self, user_id: str, trip_id: UUID) -> Optional[dict]:
        """Get trip itinerary.

        Args:
            user_id: User ID
            trip_id: Trip ID

        Returns:
            Trip itinerary data

        Raises:
            ServiceError: If retrieval fails
        """
        try:
            logger.info(f"Getting trip itinerary {trip_id} for user: {user_id}")

            # Get trip first to ensure access
            trip = await self.get_trip(user_id, trip_id)
            if not trip:
                return None

            # TODO: Get actual itinerary data from core service
            # For now, return mock data
            itinerary = {
                "id": str(uuid4()),
                "trip_id": str(trip_id),
                "items": [
                    {
                        "id": str(uuid4()),
                        "name": "Visit Eiffel Tower",
                        "description": "Iconic landmark visit",
                        "start_time": "2024-06-01T10:00:00Z",
                        "end_time": "2024-06-01T12:00:00Z",
                        "location": "Eiffel Tower, Paris",
                    }
                ],
                "total_items": 1,
            }

            return itinerary

        except Exception as e:
            logger.error(f"Failed to get trip itinerary: {str(e)}")
            raise ServiceError("Failed to get trip itinerary") from e

    async def export_trip(
        self, user_id: str, trip_id: UUID, format: str = "pdf"
    ) -> Optional[dict]:
        """Export trip.

        Args:
            user_id: User ID
            trip_id: Trip ID
            format: Export format

        Returns:
            Export data

        Raises:
            ServiceError: If export fails
        """
        try:
            logger.info(f"Exporting trip {trip_id} for user: {user_id}")

            # Get trip first to ensure access
            trip = await self.get_trip(user_id, trip_id)
            if not trip:
                return None

            # TODO: Implement actual export functionality
            # For now, return mock data
            export_data = {
                "format": format,
                "download_url": f"https://example.com/exports/trip-{trip_id}.{format}",
                "expires_at": "2024-01-02T00:00:00Z",
            }

            return export_data

        except Exception as e:
            logger.error(f"Failed to export trip: {str(e)}")
            raise ServiceError("Failed to export trip") from e

    def _adapt_create_trip_request(
        self, request: CreateTripRequest
    ) -> CoreTripCreateRequest:
        """Adapt create trip request to core model."""
        # Convert date to datetime with timezone
        start_datetime = datetime.combine(
            request.start_date, datetime.min.time()
        ).replace(tzinfo=timezone.utc)
        end_datetime = datetime.combine(request.end_date, datetime.min.time()).replace(
            tzinfo=timezone.utc
        )

        # Convert TripDestination to TripLocation
        trip_locations = []
        for dest in request.destinations:
            coordinates = None
            if dest.coordinates:
                coordinates = {
                    "lat": dest.coordinates.latitude,
                    "lng": dest.coordinates.longitude,
                }

            trip_location = TripLocation(
                name=dest.name,
                country=dest.country,
                city=dest.city,
                coordinates=coordinates,
                timezone=None,  # Could be populated if available
            )
            trip_locations.append(trip_location)

        # Create core trip create request
        return CoreTripCreateRequest(
            title=request.title,
            description=request.description,
            start_date=start_datetime,
            end_date=end_datetime,
            destinations=trip_locations,
            preferences=request.preferences.model_dump() if request.preferences else {},
        )

    def _adapt_update_trip_request(self, request: UpdateTripRequest) -> dict:
        """Adapt update trip request to core model."""
        updates = {}

        if request.title is not None:
            updates["title"] = request.title
        if request.description is not None:
            updates["description"] = request.description
        if request.start_date is not None:
            # Convert date to datetime with timezone
            updates["start_date"] = datetime.combine(
                request.start_date, datetime.min.time()
            ).replace(tzinfo=timezone.utc)
        if request.end_date is not None:
            # Convert date to datetime with timezone
            updates["end_date"] = datetime.combine(
                request.end_date, datetime.min.time()
            ).replace(tzinfo=timezone.utc)
        if request.destinations is not None:
            # Convert destinations to TripLocation format
            trip_locations = []
            for dest in request.destinations:
                coordinates = None
                if dest.coordinates:
                    coordinates = {
                        "lat": dest.coordinates.latitude,
                        "lng": dest.coordinates.longitude,
                    }

                trip_location = TripLocation(
                    name=dest.name,
                    country=dest.country,
                    city=dest.city,
                    coordinates=coordinates,
                    timezone=None,
                )
                trip_locations.append(trip_location)
            updates["destinations"] = trip_locations

        return updates

    def _adapt_trip_response(self, core_response) -> TripResponse:
        """Adapt core trip response to API model."""
        from tripsage_core.models.schemas_common.geographic import Coordinates
        from tripsage_core.models.schemas_common.travel import TripDestination

        # Convert TripLocation to TripDestination
        api_destinations = []
        if hasattr(core_response, "destinations") and core_response.destinations:
            for location in core_response.destinations:
                coordinates = None
                if hasattr(location, "coordinates") and location.coordinates:
                    coordinates = Coordinates(
                        latitude=location.coordinates.get("lat", 0.0),
                        longitude=location.coordinates.get("lng", 0.0),
                    )

                destination = TripDestination(
                    name=location.name,
                    country=location.country,
                    city=location.city,
                    coordinates=coordinates,
                )
                api_destinations.append(destination)

        # Handle datetime conversion safely
        start_date = core_response.start_date
        end_date = core_response.end_date

        # Convert datetime to date if needed
        if hasattr(start_date, "date"):
            start_date = start_date.date()
        if hasattr(end_date, "date"):
            end_date = end_date.date()

        # Calculate duration
        try:
            duration_days = (end_date - start_date).days
        except (TypeError, AttributeError):
            duration_days = 1

        # Handle created_at and updated_at safely
        created_at = core_response.created_at
        updated_at = core_response.updated_at

        # Convert string dates to datetime if needed
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))

        return TripResponse(
            id=core_response.id,
            user_id=core_response.user_id,
            title=core_response.title,
            description=core_response.description,
            start_date=start_date,
            end_date=end_date,
            duration_days=duration_days,
            destinations=api_destinations,
            preferences=core_response.preferences,
            status=core_response.status,
            created_at=created_at,
            updated_at=updated_at,
        )


# Module-level dependency annotation
_core_trip_service_dep = Depends(get_core_trip_service)


# Dependency function for FastAPI
async def get_trip_service(
    core_trip_service: CoreTripService = _core_trip_service_dep,
) -> TripService:
    """
    Get trip service instance for dependency injection.

    Args:
        core_trip_service: Core trip service

    Returns:
        TripService instance
    """
    return TripService(core_trip_service=core_trip_service)
