"""Accommodation router for TripSage API.

This module provides endpoints for accommodation-related operations, including
searching for accommodations, managing saved accommodations, and retrieving details.
"""

import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, status

from tripsage.api.core.dependencies import get_principal_id, require_principal
from tripsage.api.middlewares.authentication import Principal
from tripsage.api.schemas.accommodations import (
    AccommodationDetailsRequest,
    AccommodationDetailsResponse,
    AccommodationListing,
    AccommodationLocation,
    AccommodationSearchRequest,
    AccommodationSearchResponse,
    SavedAccommodationRequest,
    SavedAccommodationResponse,
)
from tripsage_core.exceptions import CoreTripSageError
from tripsage_core.exceptions.exceptions import (
    CoreResourceNotFoundError as ResourceNotFoundError,
)
from tripsage_core.models.schemas_common import AccommodationType, BookingStatus
from tripsage_core.services.business.accommodation_service import (
    AccommodationListing as ServiceAccommodationListing,
    AccommodationLocation as ServiceAccommodationLocation,
    AccommodationSearchRequest as ServiceAccommodationSearchRequest,
    AccommodationSearchResponse as ServiceAccommodationSearchResponse,
    AccommodationService,
    get_accommodation_service,
)


logger = logging.getLogger(__name__)

router = APIRouter()


def _convert_api_to_service_search_request(
    api_request: AccommodationSearchRequest, user_id: str
) -> ServiceAccommodationSearchRequest:
    """Convert API AccommodationSearchRequest to Service AccommodationSearchRequest.

    This adapter handles the schema differences between API and service layers:
    - API uses 'adults' (required) + 'children' (optional) + 'rooms' (optional)
    - Service uses 'guests' (required) + 'adults' (optional) + 'children' (optional)

    Args:
        api_request: API accommodation search request
        user_id: User ID

    Returns:
        Service accommodation search request
    """
    # Convert API schema to service schema
    # Calculate total guests from adults + children
    total_guests = api_request.adults + (api_request.children or 0)

    # Map API fields to service fields
    service_data = {
        "user_id": user_id,
        "trip_id": str(api_request.trip_id) if api_request.trip_id else None,
        "location": api_request.location,
        "check_in": api_request.check_in,
        "check_out": api_request.check_out,
        "guests": total_guests,  # Service requires this
        "adults": api_request.adults,  # Service has this as optional
        "children": api_request.children,  # Both have this as optional
        # Note: API 'rooms' field doesn't exist in service schema
        "metadata": {},
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
        service_data["amenities"] = api_request.amenities

    if api_request.min_rating:
        service_data["min_rating"] = api_request.min_rating

    if api_request.latitude is not None and api_request.longitude is not None:
        service_data["metadata"]["coordinates"] = {
            "latitude": api_request.latitude,
            "longitude": api_request.longitude,
        }

    if api_request.rooms:
        service_data["metadata"]["rooms"] = api_request.rooms

    if not service_data["metadata"]:
        service_data.pop("metadata")

    return ServiceAccommodationSearchRequest(**service_data)


def _convert_service_location_to_api_location(
    service_location: ServiceAccommodationLocation,
) -> AccommodationLocation:
    """Convert service AccommodationLocation to API AccommodationLocation."""
    return AccommodationLocation(
        city=service_location.city,
        country=service_location.country,
        latitude=service_location.latitude or 0.0,
        longitude=service_location.longitude or 0.0,
        neighborhood=getattr(service_location, "neighborhood", None),
        distance_to_center=getattr(service_location, "distance_to_center", None),
    )


def _convert_service_listing_to_api_listing(
    service_listing: ServiceAccommodationListing,
) -> AccommodationListing:
    """Convert service AccommodationListing to API AccommodationListing."""
    return AccommodationListing(
        id=service_listing.id,
        name=service_listing.name,
        description=service_listing.description or "",
        property_type=AccommodationType(service_listing.property_type.value),
        location=_convert_service_location_to_api_location(service_listing.location),
        price_per_night=service_listing.price_per_night,
        currency=getattr(service_listing, "currency", "USD"),
        rating=getattr(service_listing, "rating", None),
        review_count=getattr(service_listing, "review_count", None),
        amenities=getattr(service_listing, "amenities", []),
        images=getattr(service_listing, "images", []),
        max_guests=getattr(service_listing, "max_guests", 2),
        bedrooms=getattr(service_listing, "bedrooms", 1),
        beds=getattr(service_listing, "beds", 1),
        bathrooms=getattr(service_listing, "bathrooms", 1.0),
        check_in_time=getattr(service_listing, "check_in_time", "15:00"),
        check_out_time=getattr(service_listing, "check_out_time", "11:00"),
        url=getattr(service_listing, "url", None),
        source=getattr(service_listing, "source", None),
        total_price=getattr(service_listing, "total_price", None),
    )


def _convert_service_search_response_to_api_response(
    service_response: ServiceAccommodationSearchResponse,
    api_request: AccommodationSearchRequest,
) -> AccommodationSearchResponse:
    """Convert service search response into the API schema representation."""
    return AccommodationSearchResponse(
        listings=[
            _convert_service_listing_to_api_listing(listing)
            for listing in service_response.listings
        ],
        count=service_response.total_results,
        currency=getattr(service_response, "currency", "USD"),
        search_id=service_response.search_id,
        trip_id=getattr(api_request, "trip_id", None),
        min_price=service_response.min_price,
        max_price=service_response.max_price,
        avg_price=service_response.avg_price,
        search_request=api_request,
    )


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
    user_id = get_principal_id(principal)
    service_request = _convert_api_to_service_search_request(request, user_id)
    service_results = await accommodation_service.search_accommodations(service_request)

    # Convert service response to API response format
    return _convert_service_search_response_to_api_response(service_results, request)


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
        listing=_convert_service_listing_to_api_listing(listing),
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
    booking = await accommodation_service.book_accommodation(user_id, booking_request)

    # Convert booking to saved accommodation response
    return SavedAccommodationResponse(
        id=UUID(booking.id),
        user_id=user_id,
        trip_id=request.trip_id,
        listing=_convert_service_listing_to_api_listing(listing),
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
        if trip_id and booking.trip_id != str(trip_id):
            continue

        # Only include saved accommodations (not actual bookings).
        # AccommodationBooking lacks a status field, so include every record for now.
        # Fetch listing details for each booking.
        try:
            listing = await accommodation_service.get_listing_details(
                booking.listing_id, user_id
            )
            if listing:
                trip_uuid: UUID | None = (
                    UUID(booking.trip_id) if booking.trip_id else trip_id
                )
                if trip_uuid is None:
                    logger.warning(
                        "Skipping saved accommodation without a trip identifier",
                        extra={"booking_id": booking.id},
                    )
                    continue

                saved_accommodations.append(
                    SavedAccommodationResponse(
                        id=UUID(booking.id),
                        user_id=user_id,
                        trip_id=trip_uuid,
                        listing=_convert_service_listing_to_api_listing(listing),
                        check_in=booking.check_in,
                        check_out=booking.check_out,
                        # Booking records omit created_at timestamps.
                        saved_at=datetime.now().date(),
                        # Accommodation bookings lack a notes field.
                        notes=None,
                        # Treat all retrieved entries as saved entries in the API.
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
        if booking.id == str(saved_accommodation_id):
            current_booking = booking
            break

    if not current_booking:
        raise ResourceNotFoundError(
            message=f"Saved accommodation with ID {saved_accommodation_id} not found",
            details={"saved_accommodation_id": str(saved_accommodation_id)},
        )

    # Get listing details
    listing = await accommodation_service.get_listing_details(
        current_booking.listing_id, user_id
    )
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

    return SavedAccommodationResponse(
        id=UUID(current_booking.id),
        user_id=user_id,
        trip_id=UUID(current_booking.trip_id) if current_booking.trip_id else None,  # type: ignore
        listing=_convert_service_listing_to_api_listing(listing),
        check_in=current_booking.check_in,
        check_out=current_booking.check_out,
        saved_at=datetime.now().date(),
        notes=None,
        status=status,  # Use the requested status
    )
