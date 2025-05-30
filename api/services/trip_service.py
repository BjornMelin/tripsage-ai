"""
Trip service for the API layer.

This service acts as a thin wrapper around the core trip service,
handling API-specific concerns like model adaptation and FastAPI integration.
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import Depends

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
            try:
                self.core_trip_service = await get_core_trip_service()
            except Exception as e:
                logger.warning(f"Could not initialize CoreTripService: {e}")
                # For now, we'll create a mock service that raises NotImplementedError
                # This allows the application to start even if the database isn't configured
                self.core_trip_service = MockTripService()
        return self.core_trip_service

    async def create_trip(
        self, user_id: str, trip_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a new trip.

        Args:
            user_id: User ID
            trip_data: Trip creation data

        Returns:
            Created trip information

        Raises:
            ValidationError: If trip data is invalid
            ServiceError: If creation fails
        """
        try:
            core_service = await self._get_core_trip_service()
            result = await core_service.create_trip(user_id=user_id, **trip_data)

            logger.info(f"Trip created successfully for user {user_id}")
            return result

        except (ValidationError, ServiceError) as e:
            logger.error(f"Failed to create trip for user {user_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating trip for user {user_id}: {e}")
            raise ServiceError("Failed to create trip") from e

    async def get_trip(self, trip_id: UUID, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a trip by ID.

        Args:
            trip_id: Trip ID
            user_id: User ID

        Returns:
            Trip information or None if not found

        Raises:
            ValidationError: If trip ID is invalid
            ServiceError: If retrieval fails
        """
        try:
            core_service = await self._get_core_trip_service()
            result = await core_service.get_trip(trip_id=trip_id, user_id=user_id)

            if result:
                logger.debug(f"Trip {trip_id} retrieved for user {user_id}")
            else:
                logger.warning(f"Trip {trip_id} not found for user {user_id}")

            return result

        except (ValidationError, ServiceError) as e:
            logger.error(f"Failed to get trip {trip_id} for user {user_id}: {e}")
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error getting trip {trip_id} for user {user_id}: {e}"
            )
            raise ServiceError("Failed to retrieve trip") from e

    async def get_user_trips(
        self, user_id: str, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get all trips for a user.

        Args:
            user_id: User ID
            limit: Maximum number of trips to return
            offset: Number of trips to skip

        Returns:
            List of user's trips

        Raises:
            ValidationError: If parameters are invalid
            ServiceError: If retrieval fails
        """
        try:
            # Validate parameters
            if limit <= 0 or limit > 100:
                raise ValidationError("Limit must be between 1 and 100")
            if offset < 0:
                raise ValidationError("Offset must be non-negative")

            core_service = await self._get_core_trip_service()
            result = await core_service.get_user_trips(
                user_id=user_id, limit=limit, offset=offset
            )

            logger.debug(f"Retrieved {len(result)} trips for user {user_id}")
            return result

        except (ValidationError, ServiceError) as e:
            logger.error(f"Failed to get trips for user {user_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting trips for user {user_id}: {e}")
            raise ServiceError("Failed to retrieve trips") from e

    async def update_trip(
        self, trip_id: UUID, user_id: str, updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update a trip.

        Args:
            trip_id: Trip ID
            user_id: User ID
            updates: Update data

        Returns:
            Updated trip information

        Raises:
            ValidationError: If update data is invalid
            ServiceError: If update fails
        """
        try:
            # Validate that updates is not empty
            if not updates:
                raise ValidationError("No updates provided")

            core_service = await self._get_core_trip_service()
            result = await core_service.update_trip(
                trip_id=trip_id, user_id=user_id, **updates
            )

            logger.info(f"Trip {trip_id} updated for user {user_id}")
            return result

        except (ValidationError, ServiceError) as e:
            logger.error(f"Failed to update trip {trip_id} for user {user_id}: {e}")
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error updating trip {trip_id} for user {user_id}: {e}"
            )
            raise ServiceError("Failed to update trip") from e

    async def delete_trip(self, trip_id: UUID, user_id: str) -> bool:
        """
        Delete a trip.

        Args:
            trip_id: Trip ID
            user_id: User ID

        Returns:
            True if deleted successfully

        Raises:
            ValidationError: If trip not found
            ServiceError: If deletion fails
        """
        try:
            core_service = await self._get_core_trip_service()
            result = await core_service.delete_trip(trip_id=trip_id, user_id=user_id)

            if result:
                logger.info(f"Trip {trip_id} deleted for user {user_id}")
            else:
                logger.warning(
                    f"Trip {trip_id} not found for deletion for user {user_id}"
                )
                raise ValidationError("Trip not found")

            return result

        except (ValidationError, ServiceError) as e:
            logger.error(f"Failed to delete trip {trip_id} for user {user_id}: {e}")
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error deleting trip {trip_id} for user {user_id}: {e}"
            )
            raise ServiceError("Failed to delete trip") from e

    async def search_trips(
        self,
        user_id: str,
        query: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Search trips for a user.

        Args:
            user_id: User ID
            query: Search query
            status: Trip status filter
            limit: Maximum number of trips to return
            offset: Number of trips to skip

        Returns:
            List of matching trips

        Raises:
            ValidationError: If parameters are invalid
            ServiceError: If search fails
        """
        try:
            # Validate parameters
            if limit <= 0 or limit > 100:
                raise ValidationError("Limit must be between 1 and 100")
            if offset < 0:
                raise ValidationError("Offset must be non-negative")

            core_service = await self._get_core_trip_service()

            # Check if core service supports search
            if hasattr(core_service, "search_trips"):
                result = await core_service.search_trips(
                    user_id=user_id,
                    query=query,
                    status=status,
                    limit=limit,
                    offset=offset,
                )
            else:
                # Fallback to get_user_trips if search not implemented
                logger.warning(
                    "Core service doesn't support search, falling back to get_user_trips"
                )
                result = await core_service.get_user_trips(user_id=user_id, limit=limit)

                # Simple client-side filtering if query provided
                if query:
                    query_lower = query.lower()
                    result = [
                        trip
                        for trip in result
                        if query_lower in trip.get("name", "").lower()
                        or query_lower in trip.get("description", "").lower()
                    ]

                # Simple status filtering
                if status:
                    result = [trip for trip in result if trip.get("status") == status]

            logger.debug(f"Search returned {len(result)} trips for user {user_id}")
            return result

        except (ValidationError, ServiceError) as e:
            logger.error(f"Failed to search trips for user {user_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error searching trips for user {user_id}: {e}")
            raise ServiceError("Failed to search trips") from e


class MockTripService:
    """Mock trip service for when the core service can't be initialized."""

    async def create_trip(self, **kwargs):
        raise ServiceError("Trip service not available - database not configured")

    async def get_trip(self, **kwargs):
        raise ServiceError("Trip service not available - database not configured")

    async def get_user_trips(self, **kwargs):
        raise ServiceError("Trip service not available - database not configured")

    async def update_trip(self, **kwargs):
        raise ServiceError("Trip service not available - database not configured")

    async def delete_trip(self, **kwargs):
        raise ServiceError("Trip service not available - database not configured")


# Dependency function for FastAPI
async def get_trip_service(
    core_trip_service: CoreTripService = Depends(get_core_trip_service),
) -> TripService:
    """
    Get trip service instance for dependency injection.

    Args:
        core_trip_service: Core trip service

    Returns:
        TripService instance
    """
    return TripService(core_trip_service=core_trip_service)
