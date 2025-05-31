"""Authentication endpoints for the TripSage API.

This module provides endpoints for authentication, including user registration,
login, token refresh, logout, and user information.
"""

import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm

from api.services.auth_service import get_auth_service
from api.deps import get_settings_dependency
from tripsage.api.middlewares.auth import create_access_token, get_current_user
from tripsage.api.models.auth import (
    RefreshToken,
    Token,
    UserCreate,
    UserResponse,
)
from tripsage.api.services.user import UserService

router = APIRouter()
logger = logging.getLogger(__name__)


_user_service_singleton = UserService()


def get_user_service() -> UserService:
    """Dependency provider for the UserService singleton."""
    return _user_service_singleton


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(
    user_data: UserCreate,
):
    """Register a new user.

    Args:
        user_data: User registration data

    Returns:
        The created user

    Raises:
        HTTPException: If the email is already registered
    """
    # Get dependencies
    settings = get_settings_dependency()
    user_service = get_user_service()

    # Check if email already exists
    if await user_service.get_user_by_email(user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create the user
    user = await user_service.create_user(
        email=user_data.email,
        password=user_data.password,
        full_name=user_data.full_name,
    )

    # Log the registration event
    logger.info(f"User registered: {user.email} in environment: {settings.environment}")

    return user


# Define the OAuth2 form dependency once
oauth2_form = Depends(OAuth2PasswordRequestForm)


@router.post(
    "/token",
    response_model=Token,
    summary="Login to get access token",
)
async def login(
    form_data: OAuth2PasswordRequestForm = oauth2_form,
):
    """Login to get an access token.

    Args:
        form_data: OAuth2 password request form data

    Returns:
        The access token

    Raises:
        HTTPException: If the credentials are invalid
    """
    # Get dependencies
    settings = get_settings_dependency()
    auth_service = get_auth_service()

    # Authenticate the user
    user = await auth_service.authenticate_user(
        form_data.username,  # Username is email in our case
        form_data.password,
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token
    access_token_expires = timedelta(minutes=settings.token_expiration_minutes)
    access_token = create_access_token(
        data={"sub": user.email, "user_id": user.id},
        settings=settings,
        expires_delta=access_token_expires,
    )

    # Create refresh token
    refresh_token_expires = timedelta(days=settings.refresh_token_expiration_days)
    refresh_token = create_access_token(
        data={"sub": user.email, "user_id": user.id, "refresh": True},
        settings=settings,
        expires_delta=refresh_token_expires,
    )

    # Calculate expiration time
    expires_at = datetime.now(datetime.UTC) + access_token_expires

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_at": expires_at,
    }


@router.post(
    "/refresh",
    response_model=Token,
    summary="Refresh access token",
)
async def refresh_token(
    refresh_data: RefreshToken,
):
    """Refresh an access token.

    Args:
        refresh_data: Refresh token data

    Returns:
        New access and refresh tokens

    Raises:
        HTTPException: If the refresh token is invalid
    """
    # Get dependencies
    settings = get_settings_dependency()
    auth_service = get_auth_service()

    # Validate the refresh token
    user = await auth_service.validate_refresh_token(refresh_data.refresh_token)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create new access token
    access_token_expires = timedelta(minutes=settings.token_expiration_minutes)
    access_token = create_access_token(
        data={"sub": user.email, "user_id": user.id},
        settings=settings,
        expires_delta=access_token_expires,
    )

    # Create new refresh token
    refresh_token_expires = timedelta(days=settings.refresh_token_expiration_days)
    refresh_token = create_access_token(
        data={"sub": user.email, "user_id": user.id, "refresh": True},
        settings=settings,
        expires_delta=refresh_token_expires,
    )

    # Calculate expiration time
    expires_at = datetime.now(datetime.UTC) + access_token_expires

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_at": expires_at,
    }


@router.post(
    "/logout",
    summary="Logout the current user",
)
async def logout(response: Response):
    """Logout the current user.

    Args:
        response: FastAPI response object (for clearing cookies)

    Returns:
        Success message
    """
    # Get dependencies
    settings = get_settings_dependency()

    # Clear the refresh token cookie (if used)
    response.delete_cookie(
        key="refresh_token",
        httponly=True,
        secure=not settings.debug,
        samesite="lax",
    )

    return {"message": "Successfully logged out"}


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user information",
)
async def get_current_user_info(user_id: str = Depends(get_current_user)):
    """Get information about the currently authenticated user.

    Args:
        user_id: The ID of the current user (from token)

    Returns:
        Current user information

    Raises:
        HTTPException: If the user is not found
    """
    # Get dependencies
    user_service = get_user_service()

    # Get the user
    user = await user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user
