"""
Router for activity-related endpoints in the TripSage API.
"""

import logging
from typing import List

from fastapi import APIRouter, HTTPException, status

from tripsage.api.schemas.requests.activities import (
    ActivitySearchRequest,
    SaveActivityRequest,
)
from tripsage.api.schemas.responses.activities import (
    ActivitySearchResponse,
    SavedActivityResponse,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/search", response_model=ActivitySearchResponse)
async def search_activities(request: ActivitySearchRequest):
    """
    Search for activities based on provided criteria.
    
    Note: This endpoint is currently returning mock data as the activity service
    is not yet implemented. This router exists to prevent import errors.
    """
    logger.info(f"Activity search request: {request.destination}")
    
    # Return empty results for now - this prevents import errors
    # TODO: Implement actual activity search service
    return ActivitySearchResponse(
        activities=[],
        total=0,
        skip=0,
        limit=20,
        search_id="mock-search-id"
    )


@router.get("/{activity_id}")
async def get_activity_details(activity_id: str):
    """
    Get detailed information about a specific activity.
    
    Note: This endpoint is not yet implemented.
    """
    logger.info(f"Get activity details request: {activity_id}")
    
    # Return 501 Not Implemented for now
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Activity details endpoint not yet implemented"
    )


@router.post("/save", response_model=SavedActivityResponse)
async def save_activity(request: SaveActivityRequest):
    """
    Save an activity for a user.
    
    Note: This endpoint is not yet implemented.
    """
    logger.info(f"Save activity request: {request.activity_id}")
    
    # Return 501 Not Implemented for now
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Save activity endpoint not yet implemented"
    )


@router.get("/saved", response_model=List[SavedActivityResponse])
async def get_saved_activities():
    """
    Get all activities saved by a user.
    
    Note: This endpoint is not yet implemented.
    """
    logger.info("Get saved activities request")
    
    # Return empty list for now
    return []


@router.delete("/saved/{activity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_saved_activity(activity_id: str):
    """
    Delete a saved activity for a user.
    
    Note: This endpoint is not yet implemented.
    """
    logger.info(f"Delete saved activity request: {activity_id}")
    
    # Return 501 Not Implemented for now
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Delete saved activity endpoint not yet implemented"
    )