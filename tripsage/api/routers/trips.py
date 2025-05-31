"""Trip router for TripSage API.

This module provides endpoints for trip management, including creating,
retrieving, updating, and deleting trips.
"""

import logging

from fastapi import APIRouter, Depends, status

from api.services.trip_service import TripService, get_trip_service
from tripsage.api.middlewares.auth import get_current_user
from tripsage.api.models.trips import (
    CreateTripRequest,
    TripResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=TripResponse, status_code=status.HTTP_201_CREATED)
async def create_trip(
    trip_request: CreateTripRequest,
    user_id: str = Depends(get_current_user),
    trip_service: TripService = Depends(get_trip_service),
):
    """Create a new trip.

    Args:
        trip_request: Trip creation request
        user_id: Current user ID (from token)

    Returns:
        Created trip
    """
