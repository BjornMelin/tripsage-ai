"""
Router for activity-related endpoints in the TripSage API.
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from tripsage.api.schemas.requests.activities import (
    ActivitySearchRequest,
    SaveActivityRequest,
)
from tripsage.api.schemas.responses.activities import (
    ActivityResponse,
    ActivitySearchResponse,
    SavedActivityResponse,
)
from tripsage_core.services.business.activity_service import (
    ActivityServiceError,
    get_activity_service,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/search", response_model=ActivitySearchResponse)
async def search_activities(request: ActivitySearchRequest):
    """
    Search for activities based on provided criteria using Google Maps Places API.

    This endpoint searches for activities, attractions, and points of interest
    in the specified destination using real-time data from Google Maps.
    """
    logger.info(f"Activity search request: {request.destination}")

    try:
        activity_service = await get_activity_service()
        result = await activity_service.search_activities(request)

        logger.info(
            f"Found {len(result.activities)} activities for {request.destination}"
        )
        return result

    except ActivityServiceError as e:
        logger.error(f"Activity service error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Activity search failed: {e.message}",
        ) from e
    except Exception as e:
        logger.error(f"Unexpected error in activity search: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while searching for activities",
        ) from e


@router.get("/{activity_id}", response_model=ActivityResponse)
async def get_activity_details(activity_id: str):
    """
    Get detailed information about a specific activity.

    Retrieves comprehensive details for an activity including enhanced
    information from Google Maps Places API.
    """
    logger.info(f"Get activity details request: {activity_id}")

    try:
        activity_service = await get_activity_service()
        activity = await activity_service.get_activity_details(activity_id)

        if not activity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Activity with ID {activity_id} not found",
            )

        logger.info(f"Retrieved details for activity: {activity_id}")
        return activity

    except ActivityServiceError as e:
        logger.error(f"Activity service error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get activity details: {e.message}",
        ) from e
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting activity details: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving activity details",
        ) from e


@router.post("/save", response_model=SavedActivityResponse)
async def save_activity(request: SaveActivityRequest):
    """
    Save an activity for a user.

    Note: This endpoint stores activity preferences but requires
    user authentication and database integration.
    """
    logger.info(f"Save activity request: {request.activity_id}")

    # TODO: Implement user authentication and database storage
    # For now, return a mock response to maintain API contract
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Save activity endpoint requires user authentication implementation",
    )


@router.get("/saved", response_model=List[SavedActivityResponse])
async def get_saved_activities():
    """
    Get all activities saved by a user.

    Note: This endpoint requires user authentication and database integration.
    """
    logger.info("Get saved activities request")

    # TODO: Implement user authentication and database retrieval
    # For now, return empty list to maintain API contract
    return []


@router.delete("/saved/{activity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_saved_activity(activity_id: str):
    """
    Delete a saved activity for a user.

    Note: This endpoint requires user authentication and database integration.
    """
    logger.info(f"Delete saved activity request: {activity_id}")

    # TODO: Implement user authentication and database operations
    # For now, return 501 to maintain API contract
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=(
            "Delete saved activity endpoint requires user authentication implementation"
        ),
    )
