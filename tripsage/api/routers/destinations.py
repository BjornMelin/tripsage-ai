"""Destination router exposing the finalized destination management API."""

from fastapi import APIRouter, Depends, HTTPException, status

from tripsage.api.core.dependencies import get_principal_id, require_principal
from tripsage.api.middlewares.authentication import Principal
from tripsage.api.schemas.destinations import (
    Destination,
    DestinationRecommendation,
    DestinationRecommendationRequest,
    DestinationSearchRequest,
    DestinationSearchResponse,
    SavedDestination,
    SavedDestinationRequest,
)
from tripsage_core.exceptions.exceptions import CoreResourceNotFoundError
from tripsage_core.services.business.destination_service import (
    DestinationService,
    get_destination_service,
)


router = APIRouter()


@router.post("/search", response_model=DestinationSearchResponse)
async def search_destinations(
    request: DestinationSearchRequest,
    principal: Principal = Depends(require_principal),
    destination_service: DestinationService = Depends(get_destination_service),
) -> DestinationSearchResponse:
    """Search destinations using the consolidated destination service."""
    return await destination_service.search_destinations(request)


@router.get("/{destination_id}", response_model=Destination)
async def get_destination_details(
    destination_id: str,
    principal: Principal = Depends(require_principal),
    destination_service: DestinationService = Depends(get_destination_service),
) -> Destination:
    """Retrieve detailed information about a destination."""
    destination = await destination_service.get_destination_details(
        destination_id,
        include_weather=True,
        include_pois=True,
        include_advisory=True,
    )

    if destination is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Destination '{destination_id}' not found",
        )

    return destination


@router.post(
    "/saved",
    response_model=SavedDestination,
    status_code=status.HTTP_201_CREATED,
)
async def save_destination(
    request: SavedDestinationRequest,
    principal: Principal = Depends(require_principal),
    destination_service: DestinationService = Depends(get_destination_service),
) -> SavedDestination:
    """Save a destination for the authenticated user."""
    user_id = get_principal_id(principal)

    try:
        return await destination_service.save_destination(user_id, request)
    except CoreResourceNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error


@router.get("/saved", response_model=list[SavedDestination])
async def list_saved_destinations(
    principal: Principal = Depends(require_principal),
    destination_service: DestinationService = Depends(get_destination_service),
) -> list[SavedDestination]:
    """Return destinations saved by the authenticated user."""
    user_id = get_principal_id(principal)
    return await destination_service.get_saved_destinations(user_id)


@router.post(
    "/recommendations",
    response_model=list[DestinationRecommendation],
)
async def get_destination_recommendations(
    request: DestinationRecommendationRequest,
    principal: Principal = Depends(require_principal),
    destination_service: DestinationService = Depends(get_destination_service),
) -> list[DestinationRecommendation]:
    """Get personalized destination recommendations."""
    user_id = get_principal_id(principal)
    return await destination_service.get_destination_recommendations(
        user_id=user_id,
        recommendation_request=request,
    )
