"""Router for itinerary-related endpoints in the TripSage API."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from tripsage.api.core.dependencies import get_principal_id, require_principal
from tripsage.api.middlewares.authentication import Principal
from tripsage.api.schemas.itineraries import (
    ItineraryConflictCheckResponse,
    ItineraryCreateRequest,
    ItineraryItemCreateRequest,
    ItineraryItemResponse,
    ItineraryItemUpdateRequest,
    ItineraryOptimizeRequest,
    ItineraryOptimizeResponse,
    ItineraryResponse,
    ItinerarySearchRequest,
    ItinerarySearchResponse,
    ItineraryUpdateRequest,
)
from tripsage_core.exceptions.exceptions import (
    CoreResourceNotFoundError as ResourceNotFoundError,
)
from tripsage_core.services.business.itinerary_service import (
    ItineraryService,
    get_itinerary_service,
)


router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("", response_model=ItineraryResponse, status_code=status.HTTP_201_CREATED)
async def create_itinerary(
    request: ItineraryCreateRequest,
    principal: Principal = Depends(require_principal),
    itinerary_service: ItineraryService = Depends(get_itinerary_service),
):
    """Create a new itinerary."""
    try:
        user_id = get_principal_id(principal)
        return await itinerary_service.create_itinerary(user_id, request)
    except ValueError as e:
        logger.warning(f"Invalid itinerary creation request: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get("", response_model=list[ItineraryResponse])
async def list_itineraries(
    principal: Principal = Depends(require_principal),
    itinerary_service: ItineraryService = Depends(get_itinerary_service),
):
    """List all itineraries for the current user."""
    user_id = get_principal_id(principal)
    return await itinerary_service.list_itineraries(user_id)


@router.post("/search", response_model=ItinerarySearchResponse)
async def search_itineraries(
    request: ItinerarySearchRequest,
    principal: Principal = Depends(require_principal),
    itinerary_service: ItineraryService = Depends(get_itinerary_service),
):
    """Search for itineraries based on criteria."""
    user_id = get_principal_id(principal)
    return await itinerary_service.search_itineraries(user_id, request)


@router.get("/{itinerary_id}", response_model=ItineraryResponse)
async def get_itinerary(
    itinerary_id: str,
    principal: Principal = Depends(require_principal),
    itinerary_service: ItineraryService = Depends(get_itinerary_service),
):
    """Get a specific itinerary by ID."""
    try:
        user_id = get_principal_id(principal)
        return await itinerary_service.get_itinerary(user_id, itinerary_id)
    except ResourceNotFoundError as e:
        logger.warning(f"Itinerary not found: {itinerary_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.put("/{itinerary_id}", response_model=ItineraryResponse)
async def update_itinerary(
    itinerary_id: str,
    request: ItineraryUpdateRequest,
    principal: Principal = Depends(require_principal),
    itinerary_service: ItineraryService = Depends(get_itinerary_service),
):
    """Update an existing itinerary."""
    try:
        user_id = get_principal_id(principal)
        return await itinerary_service.update_itinerary(user_id, itinerary_id, request)
    except ResourceNotFoundError as e:
        logger.warning(f"Itinerary not found: {itinerary_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except ValueError as e:
        logger.warning(f"Invalid itinerary update request: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.delete("/{itinerary_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_itinerary(
    itinerary_id: str,
    principal: Principal = Depends(require_principal),
    itinerary_service: ItineraryService = Depends(get_itinerary_service),
):
    """Delete an itinerary."""
    try:
        user_id = get_principal_id(principal)
        await itinerary_service.delete_itinerary(user_id, itinerary_id)
    except ResourceNotFoundError as e:
        logger.warning(f"Itinerary not found: {itinerary_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.post("/{itinerary_id}/items", response_model=ItineraryItemResponse)
async def add_item_to_itinerary(
    itinerary_id: str,
    request: ItineraryItemCreateRequest,
    principal: Principal = Depends(require_principal),
    itinerary_service: ItineraryService = Depends(get_itinerary_service),
):
    """Add an item to an itinerary."""
    try:
        user_id = get_principal_id(principal)
        return await itinerary_service.add_item_to_itinerary(
            user_id, itinerary_id, request
        )
    except ResourceNotFoundError as e:
        logger.warning(f"Itinerary not found: {itinerary_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except ValueError as e:
        logger.warning(f"Invalid item creation request: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get("/{itinerary_id}/items/{item_id}", response_model=ItineraryItemResponse)
async def get_itinerary_item(
    itinerary_id: str,
    item_id: str,
    principal: Principal = Depends(require_principal),
    itinerary_service: ItineraryService = Depends(get_itinerary_service),
):
    """Get a specific item from an itinerary."""
    try:
        user_id = get_principal_id(principal)
        return await itinerary_service.get_item(user_id, itinerary_id, item_id)
    except ResourceNotFoundError as e:
        logger.warning(f"Item not found: {item_id} in itinerary {itinerary_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.put("/{itinerary_id}/items/{item_id}", response_model=ItineraryItemResponse)
async def update_itinerary_item(
    itinerary_id: str,
    item_id: str,
    request: ItineraryItemUpdateRequest,
    principal: Principal = Depends(require_principal),
    itinerary_service: ItineraryService = Depends(get_itinerary_service),
):
    """Update an item in an itinerary."""
    try:
        user_id = get_principal_id(principal)
        return await itinerary_service.update_item(
            user_id, itinerary_id, item_id, request
        )
    except ResourceNotFoundError as e:
        logger.warning(f"Item not found: {item_id} in itinerary {itinerary_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except ValueError as e:
        logger.warning(f"Invalid item update request: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.delete(
    "/{itinerary_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_itinerary_item(
    itinerary_id: str,
    item_id: str,
    principal: Principal = Depends(require_principal),
    itinerary_service: ItineraryService = Depends(get_itinerary_service),
):
    """Delete an item from an itinerary."""
    try:
        user_id = get_principal_id(principal)
        await itinerary_service.delete_item(user_id, itinerary_id, item_id)
    except ResourceNotFoundError as e:
        logger.warning(f"Item not found: {item_id} in itinerary {itinerary_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.get("/{itinerary_id}/conflicts", response_model=ItineraryConflictCheckResponse)
async def check_itinerary_conflicts(
    itinerary_id: str,
    principal: Principal = Depends(require_principal),
    itinerary_service: ItineraryService = Depends(get_itinerary_service),
):
    """Check for conflicts in an itinerary schedule."""
    try:
        user_id = get_principal_id(principal)
        return await itinerary_service.check_conflicts(user_id, itinerary_id)
    except ResourceNotFoundError as e:
        logger.warning(f"Itinerary not found: {itinerary_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.post("/optimize", response_model=ItineraryOptimizeResponse)
async def optimize_itinerary(
    request: ItineraryOptimizeRequest,
    principal: Principal = Depends(require_principal),
    itinerary_service: ItineraryService = Depends(get_itinerary_service),
):
    """Optimize an itinerary based on provided settings."""
    try:
        user_id = get_principal_id(principal)
        return await itinerary_service.optimize_itinerary(user_id, request)
    except ResourceNotFoundError as e:
        logger.warning(f"Itinerary not found: {request.itinerary_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except ValueError as e:
        logger.warning(f"Invalid optimization request: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
