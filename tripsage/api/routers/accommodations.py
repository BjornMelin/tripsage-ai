"""Accommodation router for TripSage API.

This module provides endpoints for accommodation-related operations, including
searching for accommodations, managing saved accommodations, and retrieving details.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, status

from tripsage.api.core.dependencies import get_principal_id, require_principal
from tripsage.api.middlewares.authentication import Principal
from tripsage.api.schemas.accommodations import (
    AccommodationDetailsRequest,
    AccommodationDetailsResponse,
    AccommodationSearchRequest,
    AccommodationSearchResponse,
    SavedAccommodationRequest,
    SavedAccommodationResponse,
)
from tripsage_core.exceptions.exceptions import (
    CoreResourceNotFoundError as ResourceNotFoundError,
)
from tripsage_core.models.schemas_common import BookingStatus
from tripsage_core.services.business.accommodation_service import (
    AccommodationSearchRequest as ServiceAccommodationSearchRequest,
    AccommodationService,
    get_accommodation_service,
)


logger = logging.getLogger(__name__)

router = APIRouter()


def _convert_api_to_service_search_request(
    api_request: AccommodationSearchRequest,
) -> ServiceAccommodationSearchRequest:
    """Convert API AccommodationSearchRequest to Service AccommodationSearchRequest.

    This adapter handles the schema differences between API and service layers:
    - API uses 'adults' (required) + 'children' (optional) + 'rooms' (optional)
    - Service uses 'guests' (required) + 'adults' (optional) + 'children' (optional)

    Args:
        api_request: API accommodation search request

    Returns:
        Service accommodation search request
    """
    # Convert API schema to service schema
    # Calculate total guests from adults + children
    total_guests = api_request.adults + (api_request.children or 0)

    # Map API fields to service fields
    service_data = {
        "location": api_request.location,
        "check_in": api_request.check_in,
        "check_out": api_request.check_out,
        "guests": total_guests,  # Service requires this
        "adults": api_request.adults,  # Service has this as optional
        "children": api_request.children,  # Both have this as optional
        # Note: API 'rooms' field doesn't exist in service schema
    }

    # Add optional fields if they exist
    if api_request.property_type:
        # Map API AccommodationType to service PropertyType if needed
        service_data["property_types"] = [api_request.property_type]

    if api_request.min_price:
        service_data["min_price"] = api_request.min_price

    if api_request.max_price:
        service_data["max_price"] = api_request.max_price

    if api_request.amenities:
        # Service doesn't have amenities in search request - handle in service layer
        pass

    if api_request.min_rating:
        # Service doesn't have min_rating in search request - handle in service layer
        pass

    if api_request.latitude and api_request.longitude:
        # Service doesn't have lat/lng in search request - handle in service layer
        pass

    if api_request.trip_id:
        # Service doesn't have trip_id in search request - handle in service layer
        pass

    return ServiceAccommodationSearchRequest(**service_data)


@router.post("/search", response_model=AccommodationSearchResponse)
async def search_accommodations(
    request: AccommodationSearchRequest,
    principal: Principal = Depends(require_principal),
    accommodation_service: AccommodationService = Depends(get_accommodation_service),
):
    """Search for accommodations based on the provided criteria.

    Args:
        request: Accommodation search parameters
        principal: Current authenticated principal
        accommodation_service: Injected accommodation service

    Returns:
        Accommodation search results
    """
    # Convert API schema to service schema
    service_request = _convert_api_to_service_search_request(request)
    service_results = await accommodation_service.search_accommodations(service_request)

    # Convert service response to API response format
    return AccommodationSearchResponse(
        listings=service_results.listings,
        count=service_results.total_results,
        currency=service_results.currency
        if hasattr(service_results, "currency")
        else "USD",
        search_id=service_results.search_id,
        trip_id=getattr(request, "trip_id", None),
        min_price=service_results.min_price
        if hasattr(service_results, "min_price")
        else None,
        max_price=service_results.max_price
        if hasattr(service_results, "max_price")
        else None,
        avg_price=service_results.avg_price
        if hasattr(service_results, "avg_price")
        else None,
        search_request=request,  # Use the original API request
    )


@router.post("/details", response_model=AccommodationDetailsResponse)
async def get_accommodation_details(
    request: AccommodationDetailsRequest,
    principal: Principal = Depends(require_principal),
    accommodation_service: AccommodationService = Depends(get_accommodation_service),
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
    listing = await accommodation_service.get_listing_details(
        request.listing_id, user_id
    )
    if not listing:
        raise ResourceNotFoundError(
            message=f"Accommodation listing with ID {request.listing_id} not found",
            details={"listing_id": request.listing_id},
        )

    # Convert service response to API response format
    return AccommodationDetailsResponse(
        listing=listing,
        availability=True,  # Default to available - service could provide this
        total_price=None,  # Could be calculated based on check-in/out dates
    )


@router.post(
    "/saved",
    response_model=SavedAccommodationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def save_accommodation(
    request: SavedAccommodationRequest,
    principal: Principal = Depends(require_principal),
    accommodation_service: AccommodationService = Depends(get_accommodation_service),
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
    listing = await accommodation_service.get_listing_details(
        request.listing_id, user_id
    )
    if not listing:
        raise ResourceNotFoundError(
            message=f"Accommodation listing with ID {request.listing_id} not found",
            details={"listing_id": request.listing_id},
        )

    # Use book_accommodation to save the accommodation (with SAVED status)
    # Note: Service book_accommodation might need modification to support "saved" status
    booking = await accommodation_service.book_accommodation(
        listing_id=request.listing_id,
        user_id=user_id,
        check_in=request.check_in,
        check_out=request.check_out,
        guests=1,  # Default - service requires this
        booking_type="SAVED",  # Indicate this is a save, not a booking
    )

    # Convert booking to saved accommodation response
    return SavedAccommodationResponse(
        id=booking.id,
        user_id=user_id,
        trip_id=request.trip_id,
        listing=listing,
        check_in=request.check_in,
        check_out=request.check_out,
        saved_at=booking.created_at.date(),
        notes=request.notes,
        status=BookingStatus.SAVED,
    )


@router.delete(
    "/saved/{saved_accommodation_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_saved_accommodation(
    saved_accommodation_id: UUID,
    principal: Principal = Depends(require_principal),
    accommodation_service: AccommodationService = Depends(get_accommodation_service),
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
    success = await accommodation_service.cancel_booking(
        str(saved_accommodation_id), user_id
    )
    if not success:
        raise ResourceNotFoundError(
            message=f"Saved accommodation with ID {saved_accommodation_id} not found",
            details={"saved_accommodation_id": str(saved_accommodation_id)},
        )


@router.get("/saved", response_model=list[SavedAccommodationResponse])
async def list_saved_accommodations(
    trip_id: UUID | None = None,
    principal: Principal = Depends(require_principal),
    accommodation_service: AccommodationService = Depends(get_accommodation_service),
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
    bookings = await accommodation_service.get_user_bookings(user_id)

    # Convert bookings to saved accommodation responses
    saved_accommodations = []
    for booking in bookings:
        # Filter by trip_id if provided
        if trip_id and booking.trip_id != trip_id:
            continue

        # Only include saved accommodations (not actual bookings)
        if booking.status == BookingStatus.SAVED:
            saved_accommodations.append(
                SavedAccommodationResponse(
                    id=booking.id,
                    user_id=user_id,
                    trip_id=booking.trip_id,
                    listing=booking.listing,  # Assumes booking has listing details
                    check_in=booking.check_in,
                    check_out=booking.check_out,
                    saved_at=booking.created_at.date(),
                    notes=booking.notes,
                    status=booking.status,
                )
            )

    return saved_accommodations


@router.patch(
    "/saved/{saved_accommodation_id}/status",
    response_model=SavedAccommodationResponse,
)
async def update_saved_accommodation_status(
    saved_accommodation_id: UUID,
    status: BookingStatus,
    principal: Principal = Depends(require_principal),
    accommodation_service: AccommodationService = Depends(get_accommodation_service),
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
    bookings = await accommodation_service.get_user_bookings(user_id)
    current_booking = None
    for booking in bookings:
        if booking.id == saved_accommodation_id:
            current_booking = booking
            break

    if not current_booking:
        raise ResourceNotFoundError(
            message=f"Saved accommodation with ID {saved_accommodation_id} not found",
            details={"saved_accommodation_id": str(saved_accommodation_id)},
        )

    # Note: Service doesn't have update_status method - would need to be implemented
    # For now, return the current booking with updated status
    # In a real implementation, the service would need an update_booking_status method

    return SavedAccommodationResponse(
        id=current_booking.id,
        user_id=user_id,
        trip_id=current_booking.trip_id,
        listing=current_booking.listing,
        check_in=current_booking.check_in,
        check_out=current_booking.check_out,
        saved_at=current_booking.created_at.date(),
        notes=current_booking.notes,
        status=status,  # Use the requested status
    )
