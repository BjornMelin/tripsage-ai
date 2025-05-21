"""Accommodation router for TripSage API.

This module provides endpoints for accommodation-related operations, including
searching for accommodations, managing saved accommodations, and retrieving details.
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, status

from tripsage.api.core.exceptions import ResourceNotFoundError
from tripsage.api.middlewares.auth import get_current_user
from tripsage.api.models.accommodations import (
    AccommodationDetailsRequest,
    AccommodationDetailsResponse,
    AccommodationSearchRequest,
    AccommodationSearchResponse,
    BookingStatus,
    SavedAccommodationRequest,
    SavedAccommodationResponse,
)
from tripsage.api.services.accommodation import AccommodationService

logger = logging.getLogger(__name__)

router = APIRouter()

_accommodation_service_singleton = AccommodationService()


def get_accommodation_service() -> AccommodationService:
    """Dependency provider for the AccommodationService singleton."""
    return _accommodation_service_singleton


@router.post("/search", response_model=AccommodationSearchResponse)
async def search_accommodations(
    request: AccommodationSearchRequest,
    user_id: str = Depends(get_current_user),
):
    """Search for accommodations based on the provided criteria.

    Args:
        request: Accommodation search parameters
        user_id: Current user ID (from token)

    Returns:
        Accommodation search results
    """
    # Get dependencies
    accommodation_service = get_accommodation_service()

    # Search for accommodations
    results = await accommodation_service.search_accommodations(request)
    return results


@router.post("/details", response_model=AccommodationDetailsResponse)
async def get_accommodation_details(
    request: AccommodationDetailsRequest,
    user_id: str = Depends(get_current_user),
):
    """Get details of a specific accommodation listing.

    Args:
        request: Accommodation details parameters
        user_id: Current user ID (from token)

    Returns:
        Accommodation details

    Raises:
        ResourceNotFoundError: If the accommodation listing is not found
    """
    # Get dependencies
    accommodation_service = get_accommodation_service()

    # Get accommodation details
    details = await accommodation_service.get_accommodation_details(request)
    if not details:
        raise ResourceNotFoundError(
            message=f"Accommodation listing with ID {request.listing_id} not found",
            details={"listing_id": request.listing_id},
        )

    return details


@router.post(
    "/saved",
    response_model=SavedAccommodationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def save_accommodation(
    request: SavedAccommodationRequest,
    user_id: str = Depends(get_current_user),
):
    """Save an accommodation listing for a trip.

    Args:
        request: Save accommodation request
        user_id: Current user ID (from token)

    Returns:
        Saved accommodation response

    Raises:
        ResourceNotFoundError: If the accommodation listing is not found
    """
    # Get dependencies
    accommodation_service = get_accommodation_service()

    # Save the accommodation
    result = await accommodation_service.save_accommodation(user_id, request)
    if not result:
        raise ResourceNotFoundError(
            message=f"Accommodation listing with ID {request.listing_id} not found",
            details={"listing_id": request.listing_id},
        )

    return result


@router.delete(
    "/saved/{saved_accommodation_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_saved_accommodation(
    saved_accommodation_id: UUID,
    user_id: str = Depends(get_current_user),
):
    """Delete a saved accommodation.

    Args:
        saved_accommodation_id: Saved accommodation ID
        user_id: Current user ID (from token)

    Raises:
        ResourceNotFoundError: If the saved accommodation is not found
    """
    # Get dependencies
    accommodation_service = get_accommodation_service()

    # Delete the saved accommodation
    success = await accommodation_service.delete_saved_accommodation(
        user_id, saved_accommodation_id
    )
    if not success:
        raise ResourceNotFoundError(
            message=f"Saved accommodation with ID {saved_accommodation_id} not found",
            details={"saved_accommodation_id": str(saved_accommodation_id)},
        )


@router.get("/saved", response_model=List[SavedAccommodationResponse])
async def list_saved_accommodations(
    trip_id: Optional[UUID] = None,
    user_id: str = Depends(get_current_user),
):
    """List saved accommodations for a user, optionally filtered by trip.

    Args:
        trip_id: Optional trip ID to filter by
        user_id: Current user ID (from token)

    Returns:
        List of saved accommodations
    """
    # Get dependencies
    accommodation_service = get_accommodation_service()

    # List saved accommodations
    return await accommodation_service.list_saved_accommodations(user_id, trip_id)


@router.patch(
    "/saved/{saved_accommodation_id}/status",
    response_model=SavedAccommodationResponse,
)
async def update_saved_accommodation_status(
    saved_accommodation_id: UUID,
    status: BookingStatus,
    user_id: str = Depends(get_current_user),
):
    """Update the status of a saved accommodation.

    Args:
        saved_accommodation_id: Saved accommodation ID
        status: New status
        user_id: Current user ID (from token)

    Returns:
        Updated saved accommodation

    Raises:
        ResourceNotFoundError: If the saved accommodation is not found
    """
    # Get dependencies
    accommodation_service = get_accommodation_service()

    # Update the status
    result = await accommodation_service.update_saved_accommodation_status(
        user_id, saved_accommodation_id, status
    )
    if not result:
        raise ResourceNotFoundError(
            message=f"Saved accommodation with ID {saved_accommodation_id} not found",
            details={"saved_accommodation_id": str(saved_accommodation_id)},
        )

    return result
