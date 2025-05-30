"""Flight router for TripSage API.

This module provides endpoints for flight-related operations, including
searching for flights, managing saved flights, and searching for airports.
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, status

from tripsage.api.middlewares.auth import get_current_user
from tripsage.api.models.flights import (
    AirportSearchRequest,
    AirportSearchResponse,
    FlightOffer,
    FlightSearchRequest,
    FlightSearchResponse,
    MultiCityFlightSearchRequest,
    SavedFlightRequest,
    SavedFlightResponse,
)

# Note: FlightService needs to be refactored to use the new pattern
# For now, keeping the old import until it's refactored
from tripsage.api.services.flight import FlightService
from tripsage_core.exceptions.exceptions import (
    CoreResourceNotFoundError as ResourceNotFoundError,
)

logger = logging.getLogger(__name__)

router = APIRouter()

_flight_service_singleton = FlightService()


def get_flight_service() -> FlightService:
    """Dependency provider for the FlightService singleton."""
    return _flight_service_singleton


@router.post("/search", response_model=FlightSearchResponse)
async def search_flights(
    request: FlightSearchRequest,
    user_id: str = Depends(get_current_user),
):
    """Search for flights based on the provided criteria.

    Args:
        request: Flight search parameters
        user_id: Current user ID (from token)

    Returns:
        Flight search results
    """
    # Get dependencies
    flight_service = get_flight_service()

    # Search for flights
    results = await flight_service.search_flights(request)
    return results


@router.post("/search/multi-city", response_model=FlightSearchResponse)
async def search_multi_city_flights(
    request: MultiCityFlightSearchRequest,
    user_id: str = Depends(get_current_user),
):
    """Search for multi-city flights based on the provided criteria.

    Args:
        request: Multi-city flight search parameters
        user_id: Current user ID (from token)

    Returns:
        Flight search results
    """
    # Get dependencies
    flight_service = get_flight_service()

    # Search for multi-city flights
    results = await flight_service.search_multi_city_flights(request)
    return results


@router.post("/airports/search", response_model=AirportSearchResponse)
async def search_airports(
    request: AirportSearchRequest,
    user_id: str = Depends(get_current_user),
):
    """Search for airports based on the provided query.

    Args:
        request: Airport search parameters
        user_id: Current user ID (from token)

    Returns:
        Airport search results
    """
    # Get dependencies
    flight_service = get_flight_service()

    # Search for airports
    results = await flight_service.search_airports(request)
    return results


@router.get("/offers/{offer_id}", response_model=FlightOffer)
async def get_flight_offer(
    offer_id: str,
    user_id: str = Depends(get_current_user),
):
    """Get details of a specific flight offer.

    Args:
        offer_id: Flight offer ID
        user_id: Current user ID (from token)

    Returns:
        Flight offer details

    Raises:
        ResourceNotFoundError: If the flight offer is not found
    """
    # Get dependencies
    flight_service = get_flight_service()

    # Get the flight offer
    offer = await flight_service.get_flight_offer(offer_id)
    if not offer:
        raise ResourceNotFoundError(
            message=f"Flight offer with ID {offer_id} not found",
            details={"offer_id": offer_id},
        )

    return offer


@router.post(
    "/saved", response_model=SavedFlightResponse, status_code=status.HTTP_201_CREATED
)
async def save_flight(
    request: SavedFlightRequest,
    user_id: str = Depends(get_current_user),
):
    """Save a flight offer for a trip.

    Args:
        request: Save flight request
        user_id: Current user ID (from token)

    Returns:
        Saved flight response

    Raises:
        ResourceNotFoundError: If the flight offer is not found
    """
    # Get dependencies
    flight_service = get_flight_service()

    # Save the flight
    result = await flight_service.save_flight(user_id, request)
    if not result:
        raise ResourceNotFoundError(
            message=f"Flight offer with ID {request.offer_id} not found",
            details={"offer_id": request.offer_id},
        )

    return result


@router.delete("/saved/{saved_flight_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_saved_flight(
    saved_flight_id: UUID,
    user_id: str = Depends(get_current_user),
):
    """Delete a saved flight.

    Args:
        saved_flight_id: Saved flight ID
        user_id: Current user ID (from token)

    Raises:
        ResourceNotFoundError: If the saved flight is not found
    """
    # Get dependencies
    flight_service = get_flight_service()

    # Delete the saved flight
    success = await flight_service.delete_saved_flight(user_id, saved_flight_id)
    if not success:
        raise ResourceNotFoundError(
            message=f"Saved flight with ID {saved_flight_id} not found",
            details={"saved_flight_id": str(saved_flight_id)},
        )


@router.get("/saved", response_model=List[SavedFlightResponse])
async def list_saved_flights(
    trip_id: Optional[UUID] = None,
    user_id: str = Depends(get_current_user),
):
    """List saved flights for a user, optionally filtered by trip.

    Args:
        trip_id: Optional trip ID to filter by
        user_id: Current user ID (from token)

    Returns:
        List of saved flights
    """
    # Get dependencies
    flight_service = get_flight_service()

    # List saved flights
    return await flight_service.list_saved_flights(user_id, trip_id)
