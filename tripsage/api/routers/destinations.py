"""
Router for destination-related endpoints in the TripSage API.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from tripsage.api.core.dependencies import get_principal_id, require_principal
from tripsage.api.middlewares.authentication import Principal
from tripsage.api.schemas.destinations import (
    DestinationDetailsResponse,
    DestinationSearchResponse,
    PointOfInterestSearchRequest,
    SavedDestinationResponse,
)
from tripsage.api.schemas.destinations import (
    DestinationSearchRequest as APIDestinationSearchRequest,
)
from tripsage_core.exceptions.exceptions import (
    CoreResourceNotFoundError as ResourceNotFoundError,
)
from tripsage_core.models.schemas_common.geographic import Place as Destination
from tripsage_core.models.schemas_common.geographic import Place as PointOfInterest
from tripsage_core.services.business.destination_service import (
    DestinationSearchRequest as ServiceDestinationSearchRequest,
)
from tripsage_core.services.business.destination_service import (
    DestinationService,
    get_destination_service,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/search", response_model=DestinationSearchResponse)
async def search_destinations(
    request: APIDestinationSearchRequest,
    principal: Principal = Depends(require_principal),
    destination_service: DestinationService = Depends(get_destination_service),
):
    """
    Search for destinations based on provided criteria.
    """
    # Convert API schema to service schema
    service_request = ServiceDestinationSearchRequest(
        query=request.query,
        categories=request.categories,
        min_safety_rating=request.min_safety_rating,
        travel_month=request.travel_month,
        limit=request.limit,
        include_weather=request.include_weather,
        include_pois=request.include_attractions,  # Map API field to service field
    )

    service_response = await destination_service.search_destinations(service_request)

    # Convert service response to API response
    return DestinationSearchResponse(
        destinations=service_response.destinations,
        count=service_response.total_results,
        query=service_response.search_parameters.query,
    )


@router.get("/{destination_id}", response_model=DestinationDetailsResponse)
async def get_destination_details(
    destination_id: str,
    principal: Principal = Depends(require_principal),
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


@router.post("/save/{destination_id}", response_model=SavedDestinationResponse)
async def save_destination(
    destination_id: str,
    notes: Optional[str] = None,
    principal: Principal = Depends(require_principal),
    destination_service: DestinationService = Depends(get_destination_service),
):
    """
    Save a destination for a user.
    """
    try:
        user_id = get_principal_id(principal)
        return await destination_service.save_destination(
            user_id, destination_id, notes
        )
    except ResourceNotFoundError as e:
        logger.warning(f"Destination not found: {destination_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.get("/saved", response_model=List[SavedDestinationResponse])
async def get_saved_destinations(
    principal: Principal = Depends(require_principal),
    destination_service: DestinationService = Depends(get_destination_service),
):
    """
    Get all destinations saved by a user.
    """
    user_id = get_principal_id(principal)
    return await destination_service.get_saved_destinations(user_id)


@router.delete("/saved/{destination_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_saved_destination(
    destination_id: str,
    principal: Principal = Depends(require_principal),
    destination_service: DestinationService = Depends(get_destination_service),
):
    """
    Delete a saved destination for a user.
    """
    try:
        user_id = get_principal_id(principal)
        await destination_service.delete_saved_destination(user_id, destination_id)
    except ResourceNotFoundError as e:
        logger.warning(f"Saved destination not found: {destination_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.post("/points-of-interest", response_model=List[PointOfInterest])
async def search_points_of_interest(
    request: PointOfInterestSearchRequest,
    principal: Principal = Depends(require_principal),
    destination_service: DestinationService = Depends(get_destination_service),
):
    """
    Search for points of interest in a destination.
    """
    return await destination_service.search_points_of_interest(request)


@router.get("/recommendations", response_model=List[Destination])
async def get_destination_recommendations(
    principal: Principal = Depends(require_principal),
    destination_service: DestinationService = Depends(get_destination_service),
):
    """
    Get personalized destination recommendations for a user.
    """
    user_id = get_principal_id(principal)
    return await destination_service.get_destination_recommendations(user_id)
