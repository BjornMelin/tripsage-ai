"""Trip router for TripSage API.

This module provides endpoints for trip management, including creating,
retrieving, updating, and deleting trips.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from tripsage.api.core.dependencies import get_session_memory
from tripsage.api.middlewares.auth import get_current_user
from tripsage.api.models.trips import (
    CreateTripRequest,
    TripListResponse,
    TripPreferencesRequest,
    TripResponse,
    TripSummaryResponse,
    UpdateTripRequest,
)
from tripsage.api.services.trip import TripService
from tripsage_core.exceptions.exceptions import (
    CoreResourceNotFoundError as ResourceNotFoundError,
)

logger = logging.getLogger(__name__)

router = APIRouter()

_trip_service_singleton = TripService()


def get_trip_service() -> TripService:
    """Dependency provider for the TripService singleton."""
    return _trip_service_singleton


@router.post("/", response_model=TripResponse, status_code=status.HTTP_201_CREATED)
async def create_trip(
    trip_request: CreateTripRequest,
    user_id: str = Depends(get_current_user),
):
    """Create a new trip.

    Args:
        trip_request: Trip creation request
        user_id: Current user ID (from token)

    Returns:
        Created trip
    """
    # Get dependencies
    trip_service = get_trip_service()
    session_memory = get_session_memory()

    # Store trip planning request in session memory
    session_memory["trip_request"] = trip_request.model_dump()

    # Create the trip
    trip = await trip_service.create_trip(
        user_id=user_id,
        title=trip_request.title,
        description=trip_request.description,
        start_date=trip_request.start_date,
        end_date=trip_request.end_date,
        destinations=trip_request.destinations,
        preferences=trip_request.preferences,
    )

    return trip


@router.get("/", response_model=TripListResponse)
async def list_trips(
    skip: int = Query(0, ge=0, description="Skip the first N trips"),
    limit: int = Query(
        10, ge=1, le=100, description="Limit the number of trips returned"
    ),
    user_id: str = Depends(get_current_user),
):
    """List trips for the current user.

    Args:
        skip: Number of trips to skip
        limit: Maximum number of trips to return
        user_id: Current user ID (from token)

    Returns:
        List of trips
    """
    # Get dependencies
    trip_service = get_trip_service()

    # Get trips for the user
    trips, total = await trip_service.list_trips(
        user_id=user_id,
        skip=skip,
        limit=limit,
    )

    return {
        "items": trips,
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get("/{trip_id}", response_model=TripResponse)
async def get_trip(
    trip_id: UUID,
    user_id: str = Depends(get_current_user),
):
    """Get a trip by ID.

    Args:
        trip_id: Trip ID
        user_id: Current user ID (from token)
        session_memory: Session memory dictionary

    Returns:
        Trip details

    Raises:
        ResourceNotFoundError: If the trip is not found
    """
    # Get dependencies
    trip_service = get_trip_service()
    session_memory = get_session_memory()

    # Get the trip
    trip = await trip_service.get_trip(
        user_id=user_id,
        trip_id=trip_id,
    )

    if not trip:
        raise ResourceNotFoundError(
            message=f"Trip with ID {trip_id} not found",
            details={"trip_id": str(trip_id)},
        )

    # Store trip in session memory for context
    session_memory["current_trip"] = trip

    return trip


@router.put("/{trip_id}", response_model=TripResponse)
async def update_trip(
    trip_id: UUID,
    trip_request: UpdateTripRequest,
    user_id: str = Depends(get_current_user),
):
    """Update a trip.

    Args:
        trip_id: Trip ID
        trip_request: Trip update request
        user_id: Current user ID (from token)

    Returns:
        Updated trip

    Raises:
        ResourceNotFoundError: If the trip is not found
    """
    # Get dependencies
    trip_service = get_trip_service()

    # Update the trip
    trip = await trip_service.update_trip(
        user_id=user_id,
        trip_id=trip_id,
        **trip_request.model_dump(exclude_unset=True),
    )

    if not trip:
        raise ResourceNotFoundError(
            message=f"Trip with ID {trip_id} not found",
            details={"trip_id": str(trip_id)},
        )

    return trip


@router.delete("/{trip_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_trip(
    trip_id: UUID,
    user_id: str = Depends(get_current_user),
):
    """Delete a trip.

    Args:
        trip_id: Trip ID
        user_id: Current user ID (from token)

    Raises:
        ResourceNotFoundError: If the trip is not found
    """
    # Get dependencies
    trip_service = get_trip_service()

    # Delete the trip
    success = await trip_service.delete_trip(
        user_id=user_id,
        trip_id=trip_id,
    )

    if not success:
        raise ResourceNotFoundError(
            message=f"Trip with ID {trip_id} not found",
            details={"trip_id": str(trip_id)},
        )


@router.post("/{trip_id}/preferences", response_model=TripResponse)
async def update_trip_preferences(
    trip_id: UUID,
    preferences: TripPreferencesRequest,
    user_id: str = Depends(get_current_user),
):
    """Update trip preferences.

    Args:
        trip_id: Trip ID
        preferences: Trip preferences
        user_id: Current user ID (from token)

    Returns:
        Updated trip

    Raises:
        ResourceNotFoundError: If the trip is not found
    """
    # Get dependencies
    trip_service = get_trip_service()

    # Update trip preferences
    trip = await trip_service.update_trip_preferences(
        user_id=user_id,
        trip_id=trip_id,
        preferences=preferences.model_dump(),
    )

    if not trip:
        raise ResourceNotFoundError(
            message=f"Trip with ID {trip_id} not found",
            details={"trip_id": str(trip_id)},
        )

    return trip


@router.get("/{trip_id}/summary", response_model=TripSummaryResponse)
async def get_trip_summary(
    trip_id: UUID,
    user_id: str = Depends(get_current_user),
):
    """Get a summary of a trip.

    Args:
        trip_id: Trip ID
        user_id: Current user ID (from token)

    Returns:
        Trip summary

    Raises:
        ResourceNotFoundError: If the trip is not found
    """
    # Get dependencies
    trip_service = get_trip_service()

    # Get trip summary
    summary = await trip_service.get_trip_summary(
        user_id=user_id,
        trip_id=trip_id,
    )

    if not summary:
        raise ResourceNotFoundError(
            message=f"Trip with ID {trip_id} not found",
            details={"trip_id": str(trip_id)},
        )

    return summary
