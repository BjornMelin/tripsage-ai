"""User-related endpoints for the TripSage API.

This module provides endpoints for user preferences and profile management.
Simplified authentication using direct JWT verification.
"""

import logging
from collections.abc import Mapping
from typing import Any, cast

from fastapi import APIRouter, HTTPException, status

from tripsage.api.core.dependencies import RequiredPrincipalDep, get_principal_id
from tripsage.api.schemas.users import UserPreferencesRequest, UserPreferencesResponse
from tripsage_core.observability.otel import (
    http_route_attr_fn,
    record_histogram,
    trace_span,
)
from tripsage_core.services.infrastructure.supabase_user_ops import (
    get_user_preferences as supabase_get_user_preferences,
    update_user_preferences as supabase_update_user_preferences,
)


router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/preferences", response_model=UserPreferencesResponse)
@trace_span(name="api.users.preferences.get")
@record_histogram("api.op.duration", unit="s", attr_fn=http_route_attr_fn)
async def get_user_preferences(
    principal: RequiredPrincipalDep,
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
    logger.info("Getting preferences for user: %s", user_id)

    try:
        preferences = await supabase_get_user_preferences(user_id)
        return UserPreferencesResponse(preferences=preferences)
    except Exception as e:
        logger.exception("Error getting user preferences")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve preferences",
        ) from e


@router.put("/preferences", response_model=UserPreferencesResponse)
@trace_span(name="api.users.preferences.update")
@record_histogram("api.op.duration", unit="s", attr_fn=http_route_attr_fn)
async def update_user_preferences(
    preferences_request: UserPreferencesRequest,
    principal: RequiredPrincipalDep,
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
    logger.info("Updating preferences for user: %s", user_id)

    try:
        preferences = await supabase_update_user_preferences(
            user_id,
            new_preferences=cast(Mapping[str, Any], preferences_request.preferences),
        )
        return UserPreferencesResponse(preferences=preferences)

    except Exception as e:
        logger.exception("Error updating user preferences")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update preferences",
        ) from e
