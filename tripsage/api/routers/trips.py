"""Trip router for TripSage API.

This module provides endpoints for trip management, including creating,
retrieving, updating, and deleting trips.
"""

import logging

from fastapi import APIRouter, Depends, status

from tripsage.api.core.dependencies import require_principal_dep
from tripsage.api.middlewares.authentication import Principal
from tripsage.api.models.requests.trips import CreateTripRequest
from tripsage.api.models.responses.trips import TripResponse
from tripsage_core.services.business.trip_service import (
    TripService,
    get_trip_service,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=TripResponse, status_code=status.HTTP_201_CREATED)
async def create_trip(
    trip_request: CreateTripRequest,
    principal: Principal = require_principal_dep,
    trip_service: TripService = Depends(get_trip_service),
):
    """Create a new trip.

    Args:
        trip_request: Trip creation request
        principal: Current authenticated principal

    Returns:
        Created trip
    """
