"""Router for itinerary-related endpoints in the TripSage API."""

import logging

from fastapi import APIRouter, HTTPException, status

from tripsage.api.core.dependencies import (
    ItineraryServiceDep,
    RequiredPrincipalDep,
    get_principal_id,
)
from tripsage_core.exceptions.exceptions import (
    CoreResourceNotFoundError as ResourceNotFoundError,
)
from tripsage_core.models.api.itinerary_models import (
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


router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("", response_model=ItineraryResponse, status_code=status.HTTP_201_CREATED)
async def create_itinerary(
    request: ItineraryCreateRequest,
    itinerary_service: ItineraryServiceDep,
    principal: RequiredPrincipalDep,
):
    """Create a new itinerary."""
    try:
        user_id = get_principal_id(principal)
        return await itinerary_service.create_itinerary(user_id, request)
    except ValueError as e:
        logger.warning("Invalid itinerary creation request: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get("", response_model=list[ItineraryResponse])
async def list_itineraries(
    itinerary_service: ItineraryServiceDep,
    principal: RequiredPrincipalDep,
):
    """List all itineraries for the current user."""
    user_id = get_principal_id(principal)
    return await itinerary_service.list_itineraries(user_id)


@router.post("/search", response_model=ItinerarySearchResponse)
async def search_itineraries(
    request: ItinerarySearchRequest,
    itinerary_service: ItineraryServiceDep,
    principal: RequiredPrincipalDep,
):
    """Search for itineraries based on criteria."""
    user_id = get_principal_id(principal)
    return await itinerary_service.search_itineraries(user_id, request)


@router.get("/{itinerary_id}", response_model=ItineraryResponse)
async def get_itinerary(
    itinerary_id: str,
    itinerary_service: ItineraryServiceDep,
    principal: RequiredPrincipalDep,
):
    """Get a specific itinerary by ID."""
    try:
        user_id = get_principal_id(principal)
        return await itinerary_service.get_itinerary(user_id, itinerary_id)
    except ResourceNotFoundError as e:
        logger.warning("Itinerary not found: %s", itinerary_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.put("/{itinerary_id}", response_model=ItineraryResponse)
async def update_itinerary(
    itinerary_id: str,
    request: ItineraryUpdateRequest,
    itinerary_service: ItineraryServiceDep,
    principal: RequiredPrincipalDep,
):
    """Update an existing itinerary."""
    try:
        user_id = get_principal_id(principal)
        return await itinerary_service.update_itinerary(user_id, itinerary_id, request)
    except ResourceNotFoundError as e:
        logger.warning("Itinerary not found: %s", itinerary_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except ValueError as e:
        logger.warning("Invalid itinerary update request: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.delete("/{itinerary_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_itinerary(
    itinerary_id: str,
    itinerary_service: ItineraryServiceDep,
    principal: RequiredPrincipalDep,
):
    """Delete an itinerary."""
    try:
        user_id = get_principal_id(principal)
        await itinerary_service.delete_itinerary(user_id, itinerary_id)
    except ResourceNotFoundError as e:
        logger.warning("Itinerary not found: %s", itinerary_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.post("/{itinerary_id}/items", response_model=ItineraryItemResponse)
async def add_item_to_itinerary(
    itinerary_id: str,
    request: ItineraryItemCreateRequest,
    itinerary_service: ItineraryServiceDep,
    principal: RequiredPrincipalDep,
):
    """Add an item to an itinerary."""
    try:
        user_id = get_principal_id(principal)
        return await itinerary_service.add_item_to_itinerary(
            user_id, itinerary_id, request
        )
    except ResourceNotFoundError as e:
        logger.warning("Itinerary not found: %s", itinerary_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except ValueError as e:
        logger.warning("Invalid item creation request: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get("/{itinerary_id}/items/{item_id}", response_model=ItineraryItemResponse)
async def get_itinerary_item(
    itinerary_id: str,
    item_id: str,
    itinerary_service: ItineraryServiceDep,
    principal: RequiredPrincipalDep,
):
    """Get a specific item from an itinerary."""
    try:
        user_id = get_principal_id(principal)
        return await itinerary_service.get_item(user_id, itinerary_id, item_id)
    except ResourceNotFoundError as e:
        logger.warning("Item not found: %s in itinerary %s", item_id, itinerary_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.put("/{itinerary_id}/items/{item_id}", response_model=ItineraryItemResponse)
async def update_itinerary_item(
    itinerary_id: str,
    item_id: str,
    request: ItineraryItemUpdateRequest,
    itinerary_service: ItineraryServiceDep,
    principal: RequiredPrincipalDep,
):
    """Update an item in an itinerary."""
    try:
        user_id = get_principal_id(principal)
        return await itinerary_service.update_item(
            user_id, itinerary_id, item_id, request
        )
    except ResourceNotFoundError as e:
        logger.warning("Item not found: %s in itinerary %s", item_id, itinerary_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except ValueError as e:
        logger.warning("Invalid item update request: %s", e)
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
    itinerary_service: ItineraryServiceDep,
    principal: RequiredPrincipalDep,
):
    """Delete an item from an itinerary."""
    try:
        user_id = get_principal_id(principal)
        await itinerary_service.delete_item(user_id, itinerary_id, item_id)
    except ResourceNotFoundError as e:
        logger.warning("Item not found: %s in itinerary %s", item_id, itinerary_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.get("/{itinerary_id}/conflicts", response_model=ItineraryConflictCheckResponse)
async def check_itinerary_conflicts(
    itinerary_id: str,
    itinerary_service: ItineraryServiceDep,
    principal: RequiredPrincipalDep,
):
    """Check for conflicts in an itinerary schedule."""
    try:
        user_id = get_principal_id(principal)
        return await itinerary_service.check_conflicts(user_id, itinerary_id)
    except ResourceNotFoundError as e:
        logger.warning("Itinerary not found: %s", itinerary_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.post("/optimize", response_model=ItineraryOptimizeResponse)
async def optimize_itinerary(
    request: ItineraryOptimizeRequest,
    itinerary_service: ItineraryServiceDep,
    principal: RequiredPrincipalDep,
):
    """Optimize an itinerary based on provided settings."""
    try:
        user_id = get_principal_id(principal)
        return await itinerary_service.optimize_itinerary(user_id, request)
    except ResourceNotFoundError as e:
        logger.warning("Itinerary not found: %s", request.itinerary_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except ValueError as e:
        logger.warning("Invalid optimization request: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
