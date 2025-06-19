"""
User-related endpoints for the TripSage API.

This module provides endpoints for user preferences and profile management.
Simplified authentication using direct JWT verification.
"""

import logging

from fastapi import APIRouter, HTTPException, status

from tripsage.api.core.dependencies import (
    RequiredPrincipalDep,
    UserServiceDep,
    get_principal_id,
)
from tripsage.api.schemas.users import UserPreferencesRequest, UserPreferencesResponse

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/preferences", response_model=UserPreferencesResponse)
async def get_user_preferences(
    principal: RequiredPrincipalDep,
    user_service: UserServiceDep,
) -> UserPreferencesResponse:
    """Get the authenticated user's preferences.

    Args:
        principal: Authenticated principal from JWT or API key
        user_service: Injected user service

    Returns:
        UserPreferencesResponse: The user's preferences

    Raises:
        HTTPException: If user is not found
    """
    user_id = get_principal_id(principal)
    logger.info(f"Getting preferences for user: {user_id}")

    try:
        user = await user_service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # Return preferences or empty dict if none set
        preferences = user.preferences_json or {}
        return UserPreferencesResponse(preferences=preferences)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user preferences: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve preferences",
        ) from e


@router.put("/preferences", response_model=UserPreferencesResponse)
async def update_user_preferences(
    preferences_request: UserPreferencesRequest,
    principal: RequiredPrincipalDep,
    user_service: UserServiceDep,
) -> UserPreferencesResponse:
    """Update the authenticated user's preferences.

    This endpoint performs a partial update, merging the provided
    preferences with existing ones.

    Args:
        preferences_request: New preferences to set
        principal: Authenticated principal from JWT or API key
        user_service: Injected user service

    Returns:
        UserPreferencesResponse: The updated preferences

    Raises:
        HTTPException: If update fails
    """
    user_id = get_principal_id(principal)
    logger.info(f"Updating preferences for user: {user_id}")

    try:
        # Update preferences (service handles merging)
        updated_user = await user_service.update_user_preferences(
            user_id, preferences_request.preferences
        )

        return UserPreferencesResponse(preferences=updated_user.preferences or {})

    except Exception as e:
        logger.error(f"Error updating user preferences: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update preferences",
        ) from e
