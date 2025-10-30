"""Authentication endpoints for the TripSage API.

This module provides endpoints for authentication, including user registration,
login, token refresh, logout, and user information.
"""

import logging

from fastapi import APIRouter, HTTPException, status

from tripsage.api.schemas.auth import RegisterRequest, UserResponse


router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(
    user_data: RegisterRequest,
):
    """Register a new user.

    Args:
        user_data: User registration data

    Returns:
        The created user

    Raises:
        HTTPException: Always raised because Supabase manages registration.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=(
            "User registration is handled by Supabase auth; use the Supabase "
            "client SDK or hosted UI to sign up users."
        ),
    )
