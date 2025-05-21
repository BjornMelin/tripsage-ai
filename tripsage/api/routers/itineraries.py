"""
Router for itinerary-related endpoints in the TripSage API.
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from tripsage.api.core.dependencies import get_current_user
from tripsage.api.core.exceptions import ResourceNotFoundError
from tripsage.api.models.itineraries import (
    Itinerary,
    ItineraryConflictCheckResponse,
    ItineraryCreateRequest,
    ItineraryItem,
    ItineraryItemCreateRequest,
    ItineraryItemUpdateRequest,
    ItineraryOptimizeRequest,
    ItineraryOptimizeResponse,
    ItinerarySearchRequest,
    ItinerarySearchResponse,
    ItineraryUpdateRequest,
)
from tripsage.api.services.itinerary import get_itinerary_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("", response_model=Itinerary, status_code=status.HTTP_201_CREATED)
async def create_itinerary(
    request: ItineraryCreateRequest,
    user_id: str = Depends(get_current_user),
):
    """
    Create a new itinerary.
    """
    itinerary_service = get_itinerary_service()
    try:
        return await itinerary_service.create_itinerary(user_id, request)
    except ValueError as e:
        logger.warning(f"Invalid itinerary creation request: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get("", response_model=List[Itinerary])
async def list_itineraries(
    user_id: str = Depends(get_current_user),
):
    """
    List all itineraries for the current user.
    """
    itinerary_service = get_itinerary_service()
    return await itinerary_service.list_itineraries(user_id)


@router.post("/search", response_model=ItinerarySearchResponse)
async def search_itineraries(
    request: ItinerarySearchRequest,
    user_id: str = Depends(get_current_user),
):
    """
    Search for itineraries based on criteria.
    """
    itinerary_service = get_itinerary_service()
    return await itinerary_service.search_itineraries(user_id, request)


@router.get("/{itinerary_id}", response_model=Itinerary)
async def get_itinerary(
    itinerary_id: str,
    user_id: str = Depends(get_current_user),
):
    """
    Get a specific itinerary by ID.
    """
    itinerary_service = get_itinerary_service()
    try:
        return await itinerary_service.get_itinerary(user_id, itinerary_id)
    except ResourceNotFoundError as e:
        logger.warning(f"Itinerary not found: {itinerary_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.put("/{itinerary_id}", response_model=Itinerary)
async def update_itinerary(
    itinerary_id: str,
    request: ItineraryUpdateRequest,
    user_id: str = Depends(get_current_user),
):
    """
    Update an existing itinerary.
    """
    itinerary_service = get_itinerary_service()
    try:
        return await itinerary_service.update_itinerary(user_id, itinerary_id, request)
    except ResourceNotFoundError as e:
        logger.warning(f"Itinerary not found: {itinerary_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except ValueError as e:
        logger.warning(f"Invalid itinerary update request: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.delete("/{itinerary_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_itinerary(
    itinerary_id: str,
    user_id: str = Depends(get_current_user),
):
    """
    Delete an itinerary.
    """
    itinerary_service = get_itinerary_service()
    try:
        await itinerary_service.delete_itinerary(user_id, itinerary_id)
    except ResourceNotFoundError as e:
        logger.warning(f"Itinerary not found: {itinerary_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.post("/{itinerary_id}/items", response_model=ItineraryItem)
async def add_item_to_itinerary(
    itinerary_id: str,
    request: ItineraryItemCreateRequest,
    user_id: str = Depends(get_current_user),
):
    """
    Add an item to an itinerary.
    """
    itinerary_service = get_itinerary_service()
    try:
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
        logger.warning(f"Invalid item creation request: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get("/{itinerary_id}/items/{item_id}", response_model=ItineraryItem)
async def get_itinerary_item(
    itinerary_id: str,
    item_id: str,
    user_id: str = Depends(get_current_user),
):
    """
    Get a specific item from an itinerary.
    """
    itinerary_service = get_itinerary_service()
    try:
        return await itinerary_service.get_item(user_id, itinerary_id, item_id)
    except ResourceNotFoundError as e:
        logger.warning(f"Item not found: {item_id} in itinerary {itinerary_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.put("/{itinerary_id}/items/{item_id}", response_model=ItineraryItem)
async def update_itinerary_item(
    itinerary_id: str,
    item_id: str,
    request: ItineraryItemUpdateRequest,
    user_id: str = Depends(get_current_user),
):
    """
    Update an item in an itinerary.
    """
    itinerary_service = get_itinerary_service()
    try:
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
        logger.warning(f"Invalid item update request: {str(e)}")
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
    user_id: str = Depends(get_current_user),
):
    """
    Delete an item from an itinerary.
    """
    itinerary_service = get_itinerary_service()
    try:
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
    user_id: str = Depends(get_current_user),
):
    """
    Check for conflicts in an itinerary schedule.
    """
    itinerary_service = get_itinerary_service()
    try:
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
    user_id: str = Depends(get_current_user),
):
    """
    Optimize an itinerary based on provided settings.
    """
    itinerary_service = get_itinerary_service()
    try:
        return await itinerary_service.optimize_itinerary(user_id, request)
    except ResourceNotFoundError as e:
        logger.warning(f"Itinerary not found: {request.itinerary_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except ValueError as e:
        logger.warning(f"Invalid optimization request: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
