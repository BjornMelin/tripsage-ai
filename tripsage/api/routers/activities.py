"""
Router for activity-related endpoints in the TripSage API.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from tripsage.api.core.dependencies import get_principal_id, require_principal_dep
from tripsage.api.middlewares.authentication import Principal
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
async def save_activity(
    request: SaveActivityRequest,
    principal: Principal = require_principal_dep,
    activity_service=Depends(get_activity_service),
):
    """
    Save an activity for a user.

    Args:
        request: Save activity request with activity_id, trip_id, and notes
        principal: Current authenticated principal
        activity_service: Injected activity service

    Returns:
        Saved activity response
    """
    user_id = get_principal_id(principal)
    logger.info(f"Save activity request: {request.activity_id} for user {user_id}")

    try:
        # Save activity using service
        saved_data = await activity_service.save_activity(
            user_id=user_id,
            activity_id=request.activity_id,
            trip_id=request.trip_id,
        )

        # Get activity details for response
        activity_details = await activity_service.get_activity_details(
            request.activity_id
        )

        # Create response
        response = SavedActivityResponse(
            activity_id=request.activity_id,
            trip_id=request.trip_id,
            user_id=user_id,
            saved_at=saved_data.get("created_at", ""),
            notes=request.notes,
            activity=activity_details,
        )

        logger.info(
            f"Activity {request.activity_id} saved successfully for user {user_id}"
        )
        return response

    except ActivityServiceError as e:
        logger.error(f"Failed to save activity {request.activity_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to save activity: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Unexpected error saving activity {request.activity_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get("/saved", response_model=List[SavedActivityResponse])
async def get_saved_activities(
    trip_id: Optional[str] = None,
    principal: Principal = require_principal_dep,
    activity_service=Depends(get_activity_service),
):
    """
    Get all activities saved by a user.

    Args:
        trip_id: Optional trip ID to filter activities
        principal: Current authenticated principal
        activity_service: Injected activity service

    Returns:
        List of saved activities
    """
    user_id = get_principal_id(principal)
    logger.info(f"Get saved activities request for user {user_id}, trip_id: {trip_id}")

    try:
        # Get saved activities using service
        saved_activities = await activity_service.get_saved_activities(
            user_id=user_id,
            trip_id=trip_id,
        )

        # Convert to response format
        response_activities = []
        for saved_activity in saved_activities:
            # Get activity details if available
            activity_details = None
            if saved_activity.get("activity_data"):
                # Convert saved activity data to ActivityResponse
                from tripsage.api.schemas.responses.activities import (
                    ActivityCoordinates,
                    ActivityResponse,
                )

                activity_data = saved_activity["activity_data"]
                activity_details = ActivityResponse(
                    id=activity_data.get("id", ""),
                    name=activity_data.get("name", ""),
                    type=activity_data.get("type", ""),
                    location=activity_data.get("location", ""),
                    date=activity_data.get("date", ""),
                    duration=activity_data.get("duration", 0),
                    price=activity_data.get("price", 0.0),
                    rating=activity_data.get("rating", 0.0),
                    description=activity_data.get("description", ""),
                    images=activity_data.get("images", []),
                    coordinates=ActivityCoordinates(**activity_data["coordinates"])
                    if activity_data.get("coordinates")
                    else None,
                    provider=activity_data.get("provider"),
                    availability=activity_data.get("availability"),
                    cancellation_policy=activity_data.get("cancellation_policy"),
                    included=activity_data.get("included"),
                    excluded=activity_data.get("excluded"),
                    meeting_point=activity_data.get("meeting_point"),
                    languages=activity_data.get("languages"),
                    max_participants=activity_data.get("max_participants"),
                    min_participants=activity_data.get("min_participants"),
                    wheelchair_accessible=activity_data.get("wheelchair_accessible"),
                    instant_confirmation=activity_data.get("instant_confirmation"),
                )

            # Create response
            response_activity = SavedActivityResponse(
                activity_id=saved_activity.get("activity_id", ""),
                trip_id=saved_activity.get("trip_id"),
                user_id=user_id,
                saved_at=saved_activity.get("created_at", ""),
                notes=saved_activity.get("notes"),
                activity=activity_details,
            )
            response_activities.append(response_activity)

        logger.info(
            f"Retrieved {len(response_activities)} saved activities for user {user_id}"
        )
        return response_activities

    except ActivityServiceError as e:
        logger.error(f"Failed to get saved activities for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to get saved activities: {str(e)}",
        )
    except Exception as e:
        logger.error(
            f"Unexpected error getting saved activities for user {user_id}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.delete("/saved/{activity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_saved_activity(
    activity_id: str,
    principal: Principal = require_principal_dep,
    activity_service=Depends(get_activity_service),
):
    """
    Delete a saved activity for a user.

    Args:
        activity_id: Activity ID to delete from saved activities
        principal: Current authenticated principal
        activity_service: Injected activity service

    Returns:
        204 No Content on successful deletion
    """
    user_id = get_principal_id(principal)
    logger.info(f"Delete saved activity request: {activity_id} for user {user_id}")

    try:
        # Delete saved activity using service
        success = await activity_service.delete_saved_activity(
            user_id=user_id,
            activity_id=activity_id,
        )

        if not success:
            logger.warning(
                f"Activity {activity_id} not found in saved activities for user {user_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Saved activity {activity_id} not found",
            )

        logger.info(
            f"Activity {activity_id} deleted successfully from saved activities for user {user_id}"
        )
        # Return 204 No Content (FastAPI handles this automatically with the status_code)

    except ActivityServiceError as e:
        logger.error(
            f"Failed to delete saved activity {activity_id} for user {user_id}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to delete saved activity: {str(e)}",
        )
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error deleting saved activity {activity_id} for user {user_id}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )
