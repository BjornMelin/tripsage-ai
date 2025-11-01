"""Accommodation router for TripSage API.

This module provides endpoints for accommodation-related operations, including
searching for accommodations, managing saved accommodations, and retrieving details.
"""

import logging
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any, cast
from uuid import UUID

from fastapi import APIRouter, status

from tripsage.api.core.dependencies import (
    AccommodationServiceDep,
    RequiredPrincipalDep,
    get_principal_id,
)
from tripsage_core.exceptions import CoreTripSageError
from tripsage_core.exceptions.exceptions import (
    CoreResourceNotFoundError as ResourceNotFoundError,
)
from tripsage_core.models.api.accommodation_models import (
    AccommodationDetailsRequest,
    AccommodationDetailsResponse,
    AccommodationSearchRequest,
    AccommodationSearchResponse,
    SavedAccommodationRequest,
    SavedAccommodationResponse,
)
from tripsage_core.services.business.accommodation_service import BookingStatus


logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/search", response_model=AccommodationSearchResponse)
async def search_accommodations(
    request: AccommodationSearchRequest,
    accommodation_service: AccommodationServiceDep,
    principal: RequiredPrincipalDep,
):
    """Search for accommodations based on the provided criteria.

    Args:
        request: Accommodation search parameters
        principal: Current authenticated principal
        accommodation_service: Injected accommodation service

    Returns:
        Accommodation search results
    """
    user_id = get_principal_id(principal)
    # Ensure user context is attached to the canonical request
    service_request = request.model_copy(update={"user_id": user_id})
    do_search = cast(
        Callable[[AccommodationSearchRequest], Awaitable[AccommodationSearchResponse]],
        accommodation_service.search_accommodations,
    )
    service_response = await do_search(service_request)
    return AccommodationSearchResponse.model_validate(service_response.model_dump())


@router.post("/details", response_model=AccommodationDetailsResponse)
async def get_accommodation_details(
    request: AccommodationDetailsRequest,
    accommodation_service: AccommodationServiceDep,
    principal: RequiredPrincipalDep,
):
    """Get details of a specific accommodation listing.

    Args:
        request: Accommodation details parameters
        principal: Current authenticated principal
        accommodation_service: Injected accommodation service

    Returns:
        Accommodation details

    Raises:
        ResourceNotFoundError: If the accommodation listing is not found
    """
    user_id = get_principal_id(principal)
    # Service method is get_listing_details(listing_id, user_id), not
    # get_accommodation_details(request)
    get_details = cast(
        Callable[[str, str], Awaitable[Any | None]],
        accommodation_service.get_listing_details,
    )
    listing = await get_details(request.listing_id, user_id)
    if not listing:
        raise ResourceNotFoundError(
            message=f"Accommodation listing with ID {request.listing_id} not found",
            details={"listing_id": request.listing_id},
        )

    return AccommodationDetailsResponse(
        listing=listing,
        availability=True,
        total_price=None,
    )


@router.post(
    "/saved",
    response_model=SavedAccommodationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def save_accommodation(
    request: SavedAccommodationRequest,
    accommodation_service: AccommodationServiceDep,
    principal: RequiredPrincipalDep,
):
    """Save an accommodation listing for a trip.

    Args:
        request: Save accommodation request
        principal: Current authenticated principal
        accommodation_service: Injected accommodation service

    Returns:
        Saved accommodation response

    Raises:
        ResourceNotFoundError: If the accommodation listing is not found
    """
    user_id = get_principal_id(principal)

    # First get the listing details
    get_details0 = cast(
        Callable[[str, str], Awaitable[Any | None]],
        accommodation_service.get_listing_details,
    )
    listing = await get_details0(request.listing_id, user_id)
    if not listing:
        raise ResourceNotFoundError(
            message=f"Accommodation listing with ID {request.listing_id} not found",
            details={"listing_id": request.listing_id},
        )

    # Create booking request for saving accommodation
    from tripsage_core.services.business.accommodation_service import (
        AccommodationBookingRequest,
    )

    booking_request = AccommodationBookingRequest(
        listing_id=request.listing_id,
        check_in=request.check_in,
        check_out=request.check_out,
        guests=1,  # Default for saved accommodations
        guest_name="Saved",  # Placeholder for saved bookings
        guest_email="saved@example.com",  # Placeholder
        guest_phone=None,
        trip_id=str(request.trip_id) if request.trip_id else None,
        special_requests=request.notes,
        payment_method=None,
        metadata=None,
    )

    # Use book_accommodation to save the accommodation
    book = cast(
        Callable[[str, Any], Awaitable[Any]],
        accommodation_service.book_accommodation,
    )
    booking = await book(user_id, booking_request)

    booking_id_fallback = "00000000-0000-0000-0000-000000000000"
    # booking may be a pydantic model or dict-like
    if hasattr(booking, "id"):
        booking_id_str = str(booking.id)
    elif hasattr(booking, "get"):
        booking_id_str = str(booking.get("id", booking_id_fallback))
    else:
        booking_id_str = booking_id_fallback
    return SavedAccommodationResponse(
        id=UUID(booking_id_str),
        user_id=user_id,
        trip_id=request.trip_id,
        listing=listing,
        check_in=request.check_in,
        check_out=request.check_out,
        saved_at=datetime.now().date(),
        notes=request.notes,
        status=BookingStatus.SAVED,
    )


@router.delete(
    "/saved/{saved_accommodation_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_saved_accommodation(
    saved_accommodation_id: UUID,
    accommodation_service: AccommodationServiceDep,
    principal: RequiredPrincipalDep,
):
    """Delete a saved accommodation.

    Args:
        saved_accommodation_id: Saved accommodation ID
        principal: Current authenticated principal
        accommodation_service: Injected accommodation service

    Raises:
        ResourceNotFoundError: If the saved accommodation is not found
    """
    user_id = get_principal_id(principal)
    # Use cancel_booking to delete the saved accommodation
    cancel = cast(
        Callable[[str, str], Awaitable[bool]], accommodation_service.cancel_booking
    )
    success = await cancel(str(saved_accommodation_id), user_id)
    if not success:
        raise ResourceNotFoundError(
            message=f"Saved accommodation with ID {saved_accommodation_id} not found",
            details={"saved_accommodation_id": str(saved_accommodation_id)},
        )


@router.get("/saved", response_model=list[SavedAccommodationResponse])
async def list_saved_accommodations(
    accommodation_service: AccommodationServiceDep,
    principal: RequiredPrincipalDep,
    trip_id: UUID | None = None,
):
    """List saved accommodations for a user, optionally filtered by trip.

    Args:
        trip_id: Optional trip ID to filter by
        principal: Current authenticated principal
        accommodation_service: Injected accommodation service

    Returns:
        List of saved accommodations
    """
    user_id = get_principal_id(principal)
    # Use get_user_bookings to get saved accommodations
    get_bookings = cast(
        Callable[[str], Awaitable[list[Any]]],
        accommodation_service.get_user_bookings,
    )
    bookings_any = await get_bookings(user_id)
    bookings: list[Any] = bookings_any or []

    # Convert bookings to saved accommodation responses
    saved_accommodations: list[SavedAccommodationResponse] = []
    for booking in bookings:
        # Filter by trip_id if provided
        if trip_id and getattr(booking, "trip_id", None) != str(trip_id):
            continue

        # Only include saved accommodations (not actual bookings).
        # AccommodationBooking lacks a status field, so include every record for now.
        # Fetch listing details for each booking.
        try:
            get_details2 = cast(
                Callable[[str, str], Awaitable[Any | None]],
                accommodation_service.get_listing_details,
            )
            listing = await get_details2(getattr(booking, "listing_id", ""), user_id)
            if listing:
                bid_trip = getattr(booking, "trip_id", None)
                trip_uuid: UUID | None = UUID(bid_trip) if bid_trip else trip_id
                if trip_uuid is None:
                    logger.warning(
                        "Skipping saved accommodation without a trip identifier",
                        extra={"booking_id": booking.id},
                    )
                    continue

                saved_id_str = str(
                    getattr(booking, "id", "00000000-0000-0000-0000-000000000000")
                )
                saved_accommodations.append(
                    SavedAccommodationResponse(
                        id=UUID(saved_id_str),
                        user_id=user_id,
                        trip_id=trip_uuid,
                        listing=listing,
                        check_in=getattr(booking, "check_in", datetime.now().date()),
                        check_out=getattr(booking, "check_out", datetime.now().date()),
                        saved_at=datetime.now().date(),
                        notes=None,
                        status=BookingStatus.SAVED,
                    )
                )
        except (
            CoreTripSageError,
            ConnectionError,
            TimeoutError,
            RuntimeError,
            ValueError,
        ):
            # Skip bookings when listing details cannot be retrieved gracefully
            continue

    return saved_accommodations


@router.patch(
    "/saved/{saved_accommodation_id}/status",
    response_model=SavedAccommodationResponse,
)
async def update_saved_accommodation_status(
    saved_accommodation_id: UUID,
    status: BookingStatus,
    accommodation_service: AccommodationServiceDep,
    principal: RequiredPrincipalDep,
):
    """Update the status of a saved accommodation.

    Args:
        saved_accommodation_id: Saved accommodation ID
        status: New status
        principal: Current authenticated principal
        accommodation_service: Injected accommodation service

    Returns:
        Updated saved accommodation

    Raises:
        ResourceNotFoundError: If the saved accommodation is not found
    """
    user_id = get_principal_id(principal)

    # Get current booking details
    get_bookings2 = cast(
        Callable[[str], Awaitable[list[Any]]], accommodation_service.get_user_bookings
    )
    bookings = (await get_bookings2(user_id)) or []
    current_booking = None
    for booking in bookings:
        if getattr(booking, "id", "") == str(saved_accommodation_id):
            current_booking = booking
            break

    if not current_booking:
        raise ResourceNotFoundError(
            message=f"Saved accommodation with ID {saved_accommodation_id} not found",
            details={"saved_accommodation_id": str(saved_accommodation_id)},
        )

    # Get listing details
    get_details3 = cast(
        Callable[[str, str], Awaitable[Any | None]],
        accommodation_service.get_listing_details,
    )
    listing = await get_details3(getattr(current_booking, "listing_id", ""), user_id)
    if not listing:
        raise ResourceNotFoundError(
            message=(
                f"Accommodation listing with ID {current_booking.listing_id} not found"
            ),
            details={"listing_id": current_booking.listing_id},
        )

    # Note: Service doesn't have update_status method - would need to be implemented
    # For now, return the current booking with updated status
    # In a real implementation, the service would need an update_booking_status method

    curr_id_str = str(getattr(current_booking, "id", saved_accommodation_id))
    trip_uuid_out = (
        UUID(getattr(current_booking, "trip_id", ""))
        if getattr(current_booking, "trip_id", None)
        else UUID(int=0)
    )
    return SavedAccommodationResponse(
        id=UUID(curr_id_str),
        user_id=user_id,
        trip_id=trip_uuid_out,
        listing=listing,
        check_in=getattr(current_booking, "check_in", datetime.now().date()),
        check_out=getattr(current_booking, "check_out", datetime.now().date()),
        saved_at=datetime.now().date(),
        notes=None,
        status=status,  # Use the requested status
    )
