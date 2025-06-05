"""Accommodation router for TripSage API.

This module provides endpoints for accommodation-related operations, including
searching for accommodations, managing saved accommodations, and retrieving details.
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, status

from tripsage.api.core.dependencies import get_principal_id, require_principal_dep
from tripsage.api.middlewares.authentication import Principal
from tripsage.api.schemas.requests.accommodations import (
    AccommodationDetailsRequest,
    AccommodationSearchRequest,
    SavedAccommodationRequest,
)
from tripsage.api.schemas.responses.accommodations import (
    AccommodationDetailsResponse,
    AccommodationSearchResponse,
    SavedAccommodationResponse,
)
from tripsage.api.services.accommodation import (
    AccommodationService,
    get_accommodation_service,
)
from tripsage_core.exceptions.exceptions import (
    CoreResourceNotFoundError as ResourceNotFoundError,
)
from tripsage_core.models.schemas_common import BookingStatus

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/search", response_model=AccommodationSearchResponse)
async def search_accommodations(
    request: AccommodationSearchRequest,
    principal: Principal = require_principal_dep,
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
    results = await accommodation_service.search_accommodations(request)
    return results


@router.post("/details", response_model=AccommodationDetailsResponse)
async def get_accommodation_details(
    request: AccommodationDetailsRequest,
    principal: Principal = require_principal_dep,
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
    principal: Principal = require_principal_dep,
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
    principal: Principal = require_principal_dep,
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
    principal: Principal = require_principal_dep,
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
    return await accommodation_service.list_saved_accommodations(user_id, trip_id)


@router.patch(
    "/saved/{saved_accommodation_id}/status",
    response_model=SavedAccommodationResponse,
)
async def update_saved_accommodation_status(
    saved_accommodation_id: UUID,
    status: BookingStatus,
    principal: Principal = require_principal_dep,
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
    result = await accommodation_service.update_saved_accommodation_status(
        user_id, saved_accommodation_id, status
    )
    if not result:
        raise ResourceNotFoundError(
            message=f"Saved accommodation with ID {saved_accommodation_id} not found",
            details={"saved_accommodation_id": str(saved_accommodation_id)},
        )

    return result
