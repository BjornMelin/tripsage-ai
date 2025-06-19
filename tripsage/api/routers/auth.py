"""Authentication endpoints for the TripSage API.

This module provides endpoints for authentication, including user registration,
login, token refresh, logout, and user information.
"""

import logging

from fastapi import APIRouter, HTTPException, status

from tripsage.api.core.dependencies import UserServiceDep
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
    user_service: UserServiceDep,
):
    """Register a new user.

    Args:
        user_data: User registration data
        user_service: Injected user service

    Returns:
        The created user

    Raises:
        HTTPException: If the email is already registered
    """
    try:
        # Check if user already exists
        existing_user = await user_service.get_user_by_email(user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this email already exists",
            )

        # Create new user
        user = await user_service.create_user(
            email=user_data.email,
            password=user_data.password,
            full_name=user_data.full_name,
        )

        return UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            created_at=user.created_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed",
        ) from e
