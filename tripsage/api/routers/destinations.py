"""
Router for destination-related endpoints in the TripSage API.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from tripsage.api.middlewares.auth import get_current_user
from tripsage.api.models.destinations import (
    DestinationDetails,
    DestinationRecommendation,
    DestinationSearchRequest,
    DestinationSearchResponse,
    PointOfInterestSearchRequest,
    PointOfInterestSearchResponse,
    SavedDestination,
)
from tripsage.api.services.destination import (
    DestinationService,
    get_destination_service,
)
from tripsage_core.exceptions.exceptions import (
    CoreResourceNotFoundError as ResourceNotFoundError,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/search", response_model=DestinationSearchResponse)
async def search_destinations(
    request: DestinationSearchRequest,
    user_id: str = Depends(get_current_user),
    destination_service: DestinationService = Depends(get_destination_service),
):
    """
    Search for destinations based on provided criteria.
    """
    return await destination_service.search_destinations(request)


@router.get("/{destination_id}", response_model=DestinationDetails)
async def get_destination_details(
    destination_id: str,
    user_id: str = Depends(get_current_user),
    destination_service: DestinationService = Depends(get_destination_service),
):
    """
    Get detailed information about a specific destination.
    """
    try:
        return await destination_service.get_destination_details(destination_id)
    except ResourceNotFoundError as e:
        logger.warning(f"Destination not found: {destination_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.post("/save/{destination_id}", response_model=SavedDestination)
async def save_destination(
    destination_id: str,
    notes: Optional[str] = None,
    user_id: str = Depends(get_current_user),
    destination_service: DestinationService = Depends(get_destination_service),
):
    """
    Save a destination for a user.
    """
    try:
        return await destination_service.save_destination(
            user_id, destination_id, notes
        )
    except ResourceNotFoundError as e:
        logger.warning(f"Destination not found: {destination_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.get("/saved", response_model=List[SavedDestination])
async def get_saved_destinations(
    user_id: str = Depends(get_current_user),
    destination_service: DestinationService = Depends(get_destination_service),
):
    """
    Get all destinations saved by a user.
    """
    return await destination_service.get_saved_destinations(user_id)


@router.delete("/saved/{destination_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_saved_destination(
    destination_id: str,
    user_id: str = Depends(get_current_user),
    destination_service: DestinationService = Depends(get_destination_service),
):
    """
    Delete a saved destination for a user.
    """
    try:
        await destination_service.delete_saved_destination(user_id, destination_id)
    except ResourceNotFoundError as e:
        logger.warning(f"Saved destination not found: {destination_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.post("/points-of-interest", response_model=PointOfInterestSearchResponse)
async def search_points_of_interest(
    request: PointOfInterestSearchRequest,
    user_id: str = Depends(get_current_user),
    destination_service: DestinationService = Depends(get_destination_service),
):
    """
    Search for points of interest in a destination.
    """
    return await destination_service.search_points_of_interest(request)


@router.get("/recommendations", response_model=List[DestinationRecommendation])
async def get_destination_recommendations(
    user_id: str = Depends(get_current_user),
    destination_service: DestinationService = Depends(get_destination_service),
):
    """
    Get personalized destination recommendations for a user.
    """
    return await destination_service.get_destination_recommendations(user_id)
