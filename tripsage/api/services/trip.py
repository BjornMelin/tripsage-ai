"""Trip service for TripSage API.

This service acts as a thin wrapper around the core trip service,
handling API-specific concerns like model adaptation and FastAPI integration.
"""

import logging
from typing import List, Optional
from uuid import UUID

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

    def _adapt_create_trip_request(self, request: CreateTripRequest) -> dict:
        """Adapt create trip request to core model."""
        return {
            "title": request.title,
            "description": getattr(request, "description", None),
            "destination": request.destination,
            "start_date": request.start_date,
            "end_date": request.end_date,
            "budget": getattr(request, "budget", None),
            "currency": getattr(request, "currency", "USD"),
            "travelers": getattr(request, "travelers", 1),
            "trip_type": getattr(request, "trip_type", "leisure"),
            "preferences": getattr(request, "preferences", {}),
            "metadata": getattr(request, "metadata", {}),
        }

    def _adapt_update_trip_request(self, request: UpdateTripRequest) -> dict:
        """Adapt update trip request to core model."""
        updates = {}

        if hasattr(request, "title") and request.title is not None:
            updates["title"] = request.title
        if hasattr(request, "description") and request.description is not None:
            updates["description"] = request.description
        if hasattr(request, "destination") and request.destination is not None:
            updates["destination"] = request.destination
        if hasattr(request, "start_date") and request.start_date is not None:
            updates["start_date"] = request.start_date
        if hasattr(request, "end_date") and request.end_date is not None:
            updates["end_date"] = request.end_date
        if hasattr(request, "budget") and request.budget is not None:
            updates["budget"] = request.budget
        if hasattr(request, "currency") and request.currency is not None:
            updates["currency"] = request.currency
        if hasattr(request, "travelers") and request.travelers is not None:
            updates["travelers"] = request.travelers
        if hasattr(request, "trip_type") and request.trip_type is not None:
            updates["trip_type"] = request.trip_type
        if hasattr(request, "preferences") and request.preferences is not None:
            updates["preferences"] = request.preferences
        if hasattr(request, "metadata") and request.metadata is not None:
            updates["metadata"] = request.metadata

        return updates

    def _adapt_trip_response(self, core_response) -> TripResponse:
        """Adapt core trip response to API model."""
        return TripResponse(
            id=core_response.get("id", ""),
            user_id=core_response.get("user_id", ""),
            title=core_response.get("title", ""),
            description=core_response.get("description"),
            destination=core_response.get("destination", ""),
            start_date=core_response.get("start_date"),
            end_date=core_response.get("end_date"),
            budget=core_response.get("budget"),
            currency=core_response.get("currency", "USD"),
            travelers=core_response.get("travelers", 1),
            trip_type=core_response.get("trip_type", "leisure"),
            status=core_response.get("status", "planning"),
            created_at=core_response.get("created_at", ""),
            updated_at=core_response.get("updated_at", ""),
            preferences=core_response.get("preferences", {}),
            metadata=core_response.get("metadata", {}),
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
