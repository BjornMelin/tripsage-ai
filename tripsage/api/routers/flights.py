"""Flight router for TripSage API.

This module provides endpoints for flight-related operations, including
searching for flights, managing saved flights, and searching for airports.
"""

import logging
import secrets
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, status

from tripsage.api.core.dependencies import get_principal_id, require_principal
from tripsage.api.middlewares.authentication import Principal
from tripsage_core.exceptions.exceptions import (
    CoreResourceNotFoundError as ResourceNotFoundError,
)
from tripsage_core.models.domain.flight import FlightOffer
from tripsage_core.models.schemas_common.flight_schemas import (
    AirportSearchRequest,
    AirportSearchResponse,
    FlightSearchRequest,
    FlightSearchResponse,
    MultiCityFlightSearchRequest,
    SavedFlightRequest,
    SavedFlightResponse,
    UpcomingFlightResponse,
)
from tripsage_core.services.business.flight_service import (
    FlightService,
    get_flight_service,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/search", response_model=FlightSearchResponse)
async def search_flights(
    request: FlightSearchRequest,
    principal: Principal = Depends(require_principal),
    flight_service: FlightService = Depends(get_flight_service),
):
    """Search for flights based on the provided criteria.

    Args:
        request: Flight search parameters
        principal: Current authenticated principal
        flight_service: Injected flight service

    Returns:
        Flight search results
    """
    logger.debug(f"Received flight search request: {request}")
    logger.debug(f"Request type: {type(request)}")
    logger.debug(
        "Request fields: %s",
        request.model_fields if hasattr(request, "model_fields") else "No model_fields",
    )

    # Search for flights using unified schema
    results = await flight_service.search_flights(request)
    return results


@router.post("/search/multi-city", response_model=FlightSearchResponse)
async def search_multi_city_flights(
    request: MultiCityFlightSearchRequest,
    principal: Principal = Depends(require_principal),
    flight_service: FlightService = Depends(get_flight_service),
):
    """Search for multi-city flights based on the provided criteria.

    Args:
        request: Multi-city flight search parameters
        principal: Current authenticated principal
        flight_service: Injected flight service

    Returns:
        Flight search results
    """
    # Search for multi-city flights
    results = await flight_service.search_multi_city_flights(request)
    return results


@router.post("/airports/search", response_model=AirportSearchResponse)
async def search_airports(
    request: AirportSearchRequest,
    principal: Principal = Depends(require_principal),
    flight_service: FlightService = Depends(get_flight_service),
):
    """Search for airports based on the provided query.

    Args:
        request: Airport search parameters
        principal: Current authenticated principal
        flight_service: Injected flight service

    Returns:
        Airport search results
    """
    # Search for airports
    results = await flight_service.search_airports(request)
    return results


@router.get("/offers/{offer_id}", response_model=FlightOffer)
async def get_flight_offer(
    offer_id: str,
    principal: Principal = Depends(require_principal),
    flight_service: FlightService = Depends(get_flight_service),
):
    """Get details of a specific flight offer.

    Args:
        offer_id: Flight offer ID
        principal: Current authenticated principal
        flight_service: Injected flight service

    Returns:
        Flight offer details

    Raises:
        ResourceNotFoundError: If the flight offer is not found
    """
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
    principal: Principal = Depends(require_principal),
    flight_service: FlightService = Depends(get_flight_service),
):
    """Save a flight offer for a trip.

    Args:
        request: Save flight request
        principal: Current authenticated principal
        flight_service: Injected flight service

    Returns:
        Saved flight response

    Raises:
        ResourceNotFoundError: If the flight offer is not found
    """
    # Save the flight
    user_id = get_principal_id(principal)
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
    principal: Principal = Depends(require_principal),
    flight_service: FlightService = Depends(get_flight_service),
):
    """Delete a saved flight.

    Args:
        saved_flight_id: Saved flight ID
        principal: Current authenticated principal
        flight_service: Injected flight service

    Raises:
        ResourceNotFoundError: If the saved flight is not found
    """
    # Delete the saved flight
    user_id = get_principal_id(principal)
    success = await flight_service.delete_saved_flight(user_id, saved_flight_id)
    if not success:
        raise ResourceNotFoundError(
            message=f"Saved flight with ID {saved_flight_id} not found",
            details={"saved_flight_id": str(saved_flight_id)},
        )


@router.get("/saved", response_model=List[SavedFlightResponse])
async def list_saved_flights(
    trip_id: Optional[UUID] = None,
    principal: Principal = Depends(require_principal),
    flight_service: FlightService = Depends(get_flight_service),
):
    """List saved flights for a user, optionally filtered by trip.

    Args:
        trip_id: Optional trip ID to filter by
        principal: Current authenticated principal
        flight_service: Injected flight service

    Returns:
        List of saved flights
    """
    # List saved flights
    user_id = get_principal_id(principal)
    return await flight_service.list_saved_flights(user_id, trip_id)


@router.get("/upcoming", response_model=List[UpcomingFlightResponse])
async def get_upcoming_flights(
    limit: int = 10,
    include_trip_context: bool = True,
    date_range_days: int = 30,
    principal: Principal = Depends(require_principal),
    flight_service: FlightService = Depends(get_flight_service),
):
    """Get upcoming flights for a user with real-time status and trip context.

    This endpoint retrieves flights from the user's trips and saved flights,
    providing comprehensive trip context and collaboration information.

    Args:
        limit: Maximum number of flights to return
        include_trip_context: Whether to include trip information with flights
        date_range_days: Number of days ahead to search for flights
        principal: Current authenticated principal
        flight_service: Injected flight service

    Returns:
        List of upcoming flights with status and trip information
    """
    user_id = get_principal_id(principal)

    try:
        # Get upcoming flights with trip context
        upcoming_flights = await flight_service.get_upcoming_flights_with_trip_context(
            user_id=user_id,
            limit=limit,
            date_range_days=date_range_days,
            include_collaborations=include_trip_context,
        )

        return upcoming_flights

    except Exception as e:
        logger.error(f"Failed to get upcoming flights: {str(e)}")

        # Fallback to enhanced mock data with trip context
        from datetime import datetime, timedelta

        mock_flights = []
        current_time = datetime.now()

        # Generate mock data with trip context
        airlines = [
            ("AA", "American Airlines"),
            ("DL", "Delta Air Lines"),
            ("UA", "United Airlines"),
            ("B6", "JetBlue Airways"),
        ]

        airports = [
            ("JFK", "LGA", "EWR"),  # NYC area
            ("LAX", "SFO", "ORD"),  # Major destinations
            ("MIA", "ATL", "DFW"),
        ]
        airport_codes = [code for group in airports for code in group]
        destination_choices = {
            code: [other for other in airport_codes if other != code]
            for code in airport_codes
        }

        trip_names = [
            "Summer Europe Trip",
            "Business Conference - NYC",
            "Family Vacation",
            "Weekend Getaway",
            "Client Meeting - LA",
        ]

        statuses = ["upcoming", "boarding", "delayed", "cancelled"]
        terminals = ["A", "B", "C", "D"]

        for i in range(min(limit, 5)):  # Generate up to 5 mock flights
            airline_code, airline_name = secrets.choice(airlines)
            origin = secrets.choice(airport_codes)
            destination = secrets.choice(destination_choices[origin])

            search_window = max(date_range_days, 1)
            departure_time = current_time + timedelta(
                days=secrets.randbelow(search_window) + 1,
                hours=6 + secrets.randbelow(17),
                minutes=secrets.choice([0, 15, 30, 45]),
            )

            duration_minutes = 120 + secrets.randbelow(361)  # 2-8 hours
            arrival_time = departure_time + timedelta(minutes=duration_minutes)

            flight = UpcomingFlightResponse(
                id=f"flight-{i + 1}",
                airline=airline_code,
                airline_name=airline_name,
                flight_number=f"{airline_code}{secrets.randbelow(9000) + 1000}",
                origin=origin,
                destination=destination,
                departure_time=departure_time,
                arrival_time=arrival_time,
                duration=duration_minutes,
                stops=secrets.randbelow(3),
                price=300 + secrets.randbelow(901),
                currency="USD",
                cabin_class="economy",
                seats_available=10 + secrets.randbelow(41),
                status=secrets.choice(statuses),
                terminal=(
                    secrets.choice(terminals) if secrets.randbelow(10) > 2 else None
                ),
                gate=(
                    str(secrets.randbelow(50) + 1)
                    if secrets.randbelow(10) > 2
                    else None
                ),
                # Enhanced fields with trip context
                trip_id=f"trip-{i + 1}" if include_trip_context else None,
                trip_title=secrets.choice(trip_names) if include_trip_context else None,
                is_shared_trip=bool(secrets.randbelow(2))
                if include_trip_context
                else False,
                collaborator_count=secrets.randbelow(5) if include_trip_context else 0,
            )

            mock_flights.append(flight)

        # Sort by departure time
        mock_flights.sort(key=lambda f: f.departure_time)

        return mock_flights
