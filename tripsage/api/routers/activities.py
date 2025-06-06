"""Activities endpoints for the TripSage API.

This module provides endpoints for searching and managing activities.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from tripsage.api.schemas.requests.activities import (
    ActivitySearchRequest,
    SaveActivityRequest,
)
from tripsage.api.schemas.responses.activities import (
    ActivityResponse,
    ActivitySearchResponse,
    SavedActivityResponse,
)
from tripsage_core.services.business.auth_service import (
    AuthenticationService,
    get_auth_service,
)
from tripsage_core.services.business.destination_service import (
    DestinationService,
    get_destination_service,
)

router = APIRouter()
logger = logging.getLogger(__name__)
security = HTTPBearer()


@router.post(
    "/search",
    response_model=ActivitySearchResponse,
    summary="Search for activities",
    description="Search for activities at a destination with various filters",
)
async def search_activities(
    search_request: ActivitySearchRequest,
    skip: int = Query(0, ge=0, description="Number of activities to skip"),
    limit: int = Query(
        20, ge=1, le=100, description="Max number of activities to return"
    ),
    destination_service: DestinationService = Depends(get_destination_service),
):
    """Search for activities based on search criteria.

    Args:
        search_request: Activity search parameters
        skip: Pagination offset
        limit: Pagination limit
        destination_service: Injected destination service

    Returns:
        List of activities matching search criteria

    Raises:
        HTTPException: If search fails
    """
    try:
        # For now, we'll use the destination service to provide location context
        # In a full implementation, this would integrate with activity providers

        # Mock response for initial implementation
        activities: List[ActivityResponse] = []

        # TODO: Integrate with actual activity providers (Viator, GetYourGuide, etc.)
        # For now, return mock data based on destination

        if search_request.destination:
            # Mock activities based on popular destinations
            mock_activities = {
                "paris": [
                    ActivityResponse(
                        id="act-1",
                        name="Eiffel Tower Skip-the-Line Tour",
                        type="tour",
                        location="Eiffel Tower, Paris",
                        date=search_request.start_date,
                        duration=2,
                        price=89.99,
                        rating=4.8,
                        description="Skip the lines and enjoy a guided tour of the Eiffel Tower with stunning views of Paris",
                        images=["https://example.com/eiffel-tour.jpg"],
                        coordinates={"lat": 48.8584, "lng": 2.2945},
                    ),
                    ActivityResponse(
                        id="act-2",
                        name="Louvre Museum Guided Tour",
                        type="museum",
                        location="Louvre Museum, Paris",
                        date=search_request.start_date,
                        duration=3,
                        price=65.00,
                        rating=4.9,
                        description="Explore the world's largest art museum with an expert guide",
                        images=["https://example.com/louvre-tour.jpg"],
                        coordinates={"lat": 48.8606, "lng": 2.3376},
                    ),
                ],
                "tokyo": [
                    ActivityResponse(
                        id="act-3",
                        name="Mt. Fuji Day Trip from Tokyo",
                        type="day-trip",
                        location="Mt. Fuji",
                        date=search_request.start_date,
                        duration=12,
                        price=120.00,
                        rating=4.7,
                        description="Full-day guided tour to Mt. Fuji including lunch",
                        images=["https://example.com/fuji-tour.jpg"],
                        coordinates={"lat": 35.3606, "lng": 138.7274},
                    ),
                ],
                "new york": [
                    ActivityResponse(
                        id="act-4",
                        name="Broadway Show - Hamilton",
                        type="entertainment",
                        location="Richard Rodgers Theatre, NYC",
                        date=search_request.start_date,
                        duration=3,
                        price=250.00,
                        rating=4.9,
                        description="Experience the award-winning Broadway musical",
                        images=["https://example.com/hamilton.jpg"],
                        coordinates={"lat": 40.7590, "lng": -73.9865},
                    ),
                ],
            }

            destination_key = search_request.destination.lower()
            for key, acts in mock_activities.items():
                if key in destination_key:
                    activities = acts
                    break

        # Apply filters if provided
        if search_request.categories:
            activities = [a for a in activities if a.type in search_request.categories]

        if search_request.price_range:
            activities = [
                a
                for a in activities
                if search_request.price_range.min
                <= a.price
                <= search_request.price_range.max
            ]

        if search_request.rating:
            activities = [a for a in activities if a.rating >= search_request.rating]

        # Apply pagination
        total = len(activities)
        activities = activities[skip : skip + limit]

        return ActivitySearchResponse(
            activities=activities,
            total=total,
            skip=skip,
            limit=limit,
            filters_applied={
                "destination": search_request.destination,
                "categories": search_request.categories,
                "price_range": search_request.price_range.model_dump()
                if search_request.price_range
                else None,
                "rating": search_request.rating,
            },
        )

    except Exception as e:
        logger.error(f"Activity search failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search activities",
        )


@router.get(
    "/{activity_id}",
    response_model=ActivityResponse,
    summary="Get activity details",
)
async def get_activity(
    activity_id: str,
):
    """Get detailed information about a specific activity.

    Args:
        activity_id: Activity ID

    Returns:
        Activity details

    Raises:
        HTTPException: If activity not found
    """
    try:
        # TODO: Implement actual activity lookup
        # For now, return mock data

        mock_activities = {
            "act-1": ActivityResponse(
                id="act-1",
                name="Eiffel Tower Skip-the-Line Tour",
                type="tour",
                location="Eiffel Tower, Paris",
                date="2025-06-15",
                duration=2,
                price=89.99,
                rating=4.8,
                description="Skip the lines and enjoy a guided tour of the Eiffel Tower with stunning views of Paris",
                images=["https://example.com/eiffel-tour.jpg"],
                coordinates={"lat": 48.8584, "lng": 2.2945},
            ),
        }

        activity = mock_activities.get(activity_id)
        if not activity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Activity not found",
            )

        return activity

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get activity: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get activity details",
        )


@router.post(
    "/save",
    response_model=SavedActivityResponse,
    summary="Save activity to user's trip",
    status_code=status.HTTP_201_CREATED,
)
async def save_activity(
    save_request: SaveActivityRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthenticationService = Depends(get_auth_service),
):
    """Save an activity to user's trip or wishlist.

    Args:
        save_request: Activity save request
        credentials: Authorization credentials
        auth_service: Injected authentication service

    Returns:
        Saved activity confirmation

    Raises:
        HTTPException: If save fails
    """
    try:
        # Get current user
        token = credentials.credentials
        current_user = await auth_service.get_current_user(token)

        # TODO: Implement actual activity saving to trip/wishlist
        # For now, return mock confirmation

        return SavedActivityResponse(
            activity_id=save_request.activity_id,
            trip_id=save_request.trip_id,
            user_id=current_user.id,
            saved_at="2025-06-06T12:00:00Z",
            notes=save_request.notes,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to save activity: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save activity",
        )


@router.get(
    "/saved",
    response_model=List[SavedActivityResponse],
    summary="Get user's saved activities",
)
async def get_saved_activities(
    trip_id: Optional[str] = Query(None, description="Filter by trip ID"),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthenticationService = Depends(get_auth_service),
):
    """Get user's saved activities.

    Args:
        trip_id: Optional trip ID filter
        credentials: Authorization credentials
        auth_service: Injected authentication service

    Returns:
        List of saved activities

    Raises:
        HTTPException: If retrieval fails
    """
    try:
        # Get current user
        token = credentials.credentials
        current_user = await auth_service.get_current_user(token)

        # TODO: Implement actual saved activities retrieval
        # For now, return empty list

        return []

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get saved activities: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get saved activities",
        )


@router.delete(
    "/saved/{activity_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove saved activity",
)
async def remove_saved_activity(
    activity_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthenticationService = Depends(get_auth_service),
):
    """Remove a saved activity from user's trips.

    Args:
        activity_id: Activity ID to remove
        credentials: Authorization credentials
        auth_service: Injected authentication service

    Raises:
        HTTPException: If removal fails
    """
    try:
        # Get current user
        token = credentials.credentials
        current_user = await auth_service.get_current_user(token)

        # TODO: Implement actual activity removal
        # For now, just return success

        logger.info(f"Removed activity {activity_id} for user {current_user.id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove saved activity: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove saved activity",
        )
