"""
Router for authentication endpoints.

This module provides endpoints for user registration, login, token refresh,
and other authentication-related operations.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm

from api.deps import auth_service_dependency, get_current_user
from api.schemas.requests.auth import RefreshTokenRequest, RegisterUserRequest
from api.schemas.responses.auth import TokenResponse, UserResponse
from api.services.auth_service import AuthService
from tripsage_core.config.base_app_settings import settings
from tripsage_core.exceptions.exceptions import (
    CoreAuthenticationError as AuthenticationError,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Module-level dependency singletons to avoid B008 linting errors
get_current_user_dep = Depends(get_current_user)
oauth2_form_dep = Depends()


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def register(
    request: RegisterUserRequest,
    auth_service: AuthService = auth_service_dependency,
):
    """Register a new user.

    Args:
        request: User registration request

    Returns:
        Registered user information
    """
    # Check if the username or email is already taken
    if await auth_service.get_user_by_username(request.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )

    if await auth_service.get_user_by_email(request.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create the user
    user = await auth_service.create_user(
        username=request.username,
        email=request.email,
        password=request.password,
        full_name=request.full_name,
    )

    # Return user information (without password)
    return user


@router.post("/token", response_model=TokenResponse)
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = oauth2_form_dep,
    auth_service: AuthService = auth_service_dependency,
):
    """Authenticate and get access tokens.

    Args:
        response: FastAPI response object (for setting cookies)
        form_data: OAuth2 form data

    Returns:
        Access and refresh tokens
    """
    try:
        # Authenticate the user
        user = await auth_service.authenticate_user(
            username=form_data.username,
            password=form_data.password,
        )

        # Create access token
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        access_token = auth_service.create_access_token(
            data={"sub": user["id"], "username": user["username"]},
            expires_delta=access_token_expires,
        )

        # Create refresh token
        refresh_token_expires = timedelta(days=settings.refresh_token_expire_days)
        refresh_token = auth_service.create_refresh_token(
            data={"sub": user["id"]},
            expires_delta=refresh_token_expires,
        )

        # Set the refresh token as an HTTP-only cookie
        expires = datetime.now(datetime.UTC) + refresh_token_expires
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=not settings.debug,  # True in production
            samesite="lax",
            expires=expires.strftime("%a, %d %b %Y %H:%M:%S GMT"),
        )

        # Return the tokens
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.access_token_expire_minutes * 60,
        }

    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    response: Response,
    request: RefreshTokenRequest = None,
    refresh_token: Optional[str] = None,
    auth_service: AuthService = auth_service_dependency,
):
    """Refresh access token.

    Args:
        response: FastAPI response object (for setting cookies)
        request: Refresh token request (optional)
        refresh_token: Refresh token from cookie (optional)

    Returns:
        New access and refresh tokens
    """
    # Try to get refresh token from request body, then cookie
    token = None
    if request and request.refresh_token:
        token = request.refresh_token
    elif refresh_token:
        token = refresh_token

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        # Validate the refresh token
        token_data = auth_service.validate_refresh_token(token)

        # Get the user
        user = await auth_service.get_user_by_id(token_data["sub"])
        if not user:
            raise AuthenticationError("Invalid user")

        # Create a new access token
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        access_token = auth_service.create_access_token(
            data={"sub": user["id"], "username": user["username"]},
            expires_delta=access_token_expires,
        )

        # Create a new refresh token
        refresh_token_expires = timedelta(days=settings.refresh_token_expire_days)
        new_refresh_token = auth_service.create_refresh_token(
            data={"sub": user["id"]},
            expires_delta=refresh_token_expires,
        )

        # Set the new refresh token as an HTTP-only cookie
        expires = datetime.now(datetime.UTC) + refresh_token_expires
        response.set_cookie(
            key="refresh_token",
            value=new_refresh_token,
            httponly=True,
            secure=not settings.debug,  # True in production
            samesite="lax",
            expires=expires.strftime("%a, %d %b %Y %H:%M:%S GMT"),
        )

        # Return the new tokens
        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "expires_in": settings.access_token_expire_minutes * 60,
        }

    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


@router.post("/logout")
async def logout(response: Response):
    """Log out the current user.

    Args:
        response: FastAPI response object (for clearing cookies)

    Returns:
        Success message
    """
    # Clear the refresh token cookie
    response.delete_cookie(
        key="refresh_token",
        httponly=True,
        secure=not settings.debug,  # True in production
        samesite="lax",
    )

    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: dict = get_current_user_dep,
    auth_service: AuthService = auth_service_dependency,
):
    """Get information about the current user.

    Returns:
        Current user information
    """
    user = await auth_service.get_user_by_id(current_user["id"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user
