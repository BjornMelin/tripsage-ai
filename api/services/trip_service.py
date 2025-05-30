"""
Trip service for the API layer.

This module provides a trip service that wraps the TripSage Core business
trip service for use in the API layer.
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from tripsage_core.services.business.trip_service import TripService as CoreTripService

logger = logging.getLogger(__name__)


class TripService:
    """Trip service wrapper for the API layer."""

    def __init__(self):
        """Initialize the trip service."""
        # Initialize core service lazily to avoid dependency issues during import
        self._core_service = None

    def _get_core_service(self) -> CoreTripService:
        """Get or create the core service instance."""
        if self._core_service is None:
            try:
                self._core_service = CoreTripService()
            except Exception as e:
                logger.warning(f"Could not initialize CoreTripService: {e}")
                # For now, we'll create a mock service that raises NotImplementedError
                # This allows the application to start even if the database isn't configured
                self._core_service = MockTripService()
        return self._core_service

    def create_trip(self, user_id: str, trip_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new trip."""
        try:
            return self._get_core_service().create_trip(user_id=user_id, **trip_data)
        except Exception as e:
            logger.error(f"Failed to create trip: {e}")
            raise

    def get_trip(self, trip_id: UUID, user_id: str) -> Optional[Dict[str, Any]]:
        """Get a trip by ID."""
        try:
            return self._get_core_service().get_trip(trip_id=trip_id, user_id=user_id)
        except Exception as e:
            logger.error(f"Failed to get trip {trip_id}: {e}")
            raise

    def get_user_trips(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get all trips for a user."""
        try:
            return self._get_core_service().get_user_trips(user_id=user_id, limit=limit)
        except Exception as e:
            logger.error(f"Failed to get trips for user {user_id}: {e}")
            raise

    def update_trip(
        self, trip_id: UUID, user_id: str, updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update a trip."""
        try:
            return self._get_core_service().update_trip(
                trip_id=trip_id, user_id=user_id, **updates
            )
        except Exception as e:
            logger.error(f"Failed to update trip {trip_id}: {e}")
            raise

    def delete_trip(self, trip_id: UUID, user_id: str) -> bool:
        """Delete a trip."""
        try:
            return self._get_core_service().delete_trip(
                trip_id=trip_id, user_id=user_id
            )
        except Exception as e:
            logger.error(f"Failed to delete trip {trip_id}: {e}")
            raise


class MockTripService:
    """Mock trip service for when the core service can't be initialized."""

    def create_trip(self, **kwargs):
        raise NotImplementedError(
            "Trip service not available - database not configured"
        )

    def get_trip(self, **kwargs):
        raise NotImplementedError(
            "Trip service not available - database not configured"
        )

    def get_user_trips(self, **kwargs):
        raise NotImplementedError(
            "Trip service not available - database not configured"
        )

    def update_trip(self, **kwargs):
        raise NotImplementedError(
            "Trip service not available - database not configured"
        )

    def delete_trip(self, **kwargs):
        raise NotImplementedError(
            "Trip service not available - database not configured"
        )
