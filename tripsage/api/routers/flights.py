"""Flight router exposing the finalized flight management API surface.

This module provides a thin, well-typed adapter between the public FastAPI layer
and the consolidated `FlightService`. Legacy endpoints (multi-city search, saved
flight management, ad-hoc mock data) have been removed to keep the API aligned
with the maintained service capabilities and to eliminate duplicated business
logic. The remaining endpoints delegate validation and error handling to the
core service while translating domain errors into HTTP responses.
"""

# pylint: disable=duplicate-code

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from tripsage.api.core.dependencies import (
    get_flight_service_dep as get_flight_service,
    get_principal_id,
    require_principal,
)
from tripsage.api.middlewares.authentication import Principal
from tripsage.api.schemas.flights import (
    BookingStatus,
    FlightBooking,
    FlightBookingRequest,
    FlightOffer,
    FlightSearchRequest,
    FlightSearchResponse,
)
from tripsage_core.exceptions.exceptions import (
    CoreResourceNotFoundError,
    CoreServiceError,
    CoreValidationError,
)
from tripsage_core.services.business.flight_service import FlightService


router = APIRouter()


@router.post("/search", response_model=FlightSearchResponse)
async def search_flights(
    request: FlightSearchRequest,
    principal: Principal = Depends(require_principal),
    flight_service: FlightService = Depends(get_flight_service),
) -> FlightSearchResponse:
    """Search for flight offers using the unified flight service.

    Args:
        request: Typed flight search parameters validated by Pydantic.
        principal: Authenticated user context (unused directly but enforces auth).
        flight_service: Injected flight service instance.

    Returns:
        Search results including offers, metadata, and cache indicators.

    Raises:
        HTTPException: If the underlying service raises a handled error.
    """
    try:
        return await flight_service.search_flights(request)
    except CoreValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error
    except CoreServiceError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Flight search failed",
        ) from error


@router.get("/offers/{offer_id}", response_model=FlightOffer)
async def get_flight_offer(
    offer_id: str,
    principal: Principal = Depends(require_principal),
    flight_service: FlightService = Depends(get_flight_service),
) -> FlightOffer:
    """Retrieve detailed information about a specific flight offer.

    Args:
        offer_id: Identifier returned from a previous search.
        principal: Authenticated user context.
        flight_service: Injected flight service instance.

    Returns:
        Detailed flight offer information.

    Raises:
        HTTPException: 404 if the offer is unknown, 502 for service failures.
    """
    user_id = get_principal_id(principal)

    try:
        offer = await flight_service.get_offer_details(offer_id, user_id)
    except CoreServiceError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to load flight offer",
        ) from error

    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Flight offer '{offer_id}' not found",
        )

    return offer


@router.post(
    "/bookings",
    response_model=FlightBooking,
    status_code=status.HTTP_201_CREATED,
)
async def book_flight(
    request: FlightBookingRequest,
    principal: Principal = Depends(require_principal),
    flight_service: FlightService = Depends(get_flight_service),
) -> FlightBooking:
    """Book a flight offer for the authenticated user.

    Args:
        request: Booking payload containing offer and passenger data.
        principal: Authenticated user context.
        flight_service: Injected flight service.

    Returns:
        Confirmed booking details.

    Raises:
        HTTPException: 404 if the offer cannot be found, 422 for validation
        errors, and 502 for downstream failures.
    """
    user_id = get_principal_id(principal)

    try:
        return await flight_service.book_flight(user_id, request)
    except CoreResourceNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except CoreValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error
    except CoreServiceError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Flight booking failed",
        ) from error


@router.get("/bookings", response_model=list[FlightBooking])
async def list_bookings(
    trip_id: UUID | None = Query(default=None),
    status_filter: BookingStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=100),
    principal: Principal = Depends(require_principal),
    flight_service: FlightService = Depends(get_flight_service),
) -> list[FlightBooking]:
    """List bookings for the authenticated user with optional filters.

    Args:
        trip_id: Optional trip identifier filter.
        status_filter: Optional booking status filter.
        limit: Maximum number of bookings to return.
        principal: Authenticated user context.
        flight_service: Injected flight service.

    Returns:
        A list of bookings matching the provided filters.
    """
    user_id = get_principal_id(principal)

    try:
        return await flight_service.get_user_bookings(
            user_id=user_id,
            trip_id=str(trip_id) if trip_id else None,
            status=status_filter,
            limit=limit,
        )
    except CoreServiceError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch bookings",
        ) from error


@router.delete(
    "/bookings/{booking_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def cancel_booking(
    booking_id: str,
    principal: Principal = Depends(require_principal),
    flight_service: FlightService = Depends(get_flight_service),
) -> None:
    """Cancel an existing booking for the authenticated user.

    Args:
        booking_id: Identifier of the booking to cancel.
        principal: Authenticated user context.
        flight_service: Injected flight service.

    Raises:
        HTTPException: 404 if the booking is not found or cannot be cancelled,
        502 for downstream errors.
    """
    user_id = get_principal_id(principal)

    try:
        cancelled = await flight_service.cancel_booking(
            booking_id=booking_id, user_id=user_id
        )
    except CoreServiceError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to cancel booking",
        ) from error

    if not cancelled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Booking '{booking_id}' not found or cannot be cancelled",
        )
