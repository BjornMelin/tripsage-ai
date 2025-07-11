"""Authentication endpoints for the TripSage API.

This module provides endpoints for authentication, including user registration,
login, token refresh, logout, and user information.
"""

import logging

from fastapi import APIRouter, Depends, status

from tripsage.api.schemas.auth import RegisterRequest, UserResponse
from tripsage_core.services.business.user_service import UserService, get_user_service

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
    user_service: UserService = Depends(get_user_service),
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
