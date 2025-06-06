"""Authentication endpoints for the TripSage API.

This module provides endpoints for authentication, including user registration,
login, token refresh, logout, and user information.
"""

import logging
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from tripsage.api.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    PasswordResetResponse,
    RefreshTokenRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
)
from tripsage_core.services.business.auth_service import (
    AuthenticationService,
    LoginRequest as ServiceLoginRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequest as ServicePasswordResetRequest,
    RefreshTokenRequest as ServiceRefreshTokenRequest,
    get_auth_service,
)
from tripsage_core.services.business.user_service import (
    PasswordChangeRequest,
    UserCreateRequest,
    UserService,
    UserUpdateRequest,
    get_user_service,
)

router = APIRouter()
logger = logging.getLogger(__name__)
security = HTTPBearer()


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
    try:
        # Create user request for service
        create_request = UserCreateRequest(
            email=user_data.email,
            password=user_data.password,
            username=user_data.username,
            full_name=user_data.full_name,
        )
        
        # Register user
        user = await user_service.create_user(create_request)
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login user",
)
async def login(
    login_data: LoginRequest,
    auth_service: AuthenticationService = Depends(get_auth_service),
):
    """Authenticate user and return tokens.

    Args:
        login_data: Login credentials
        auth_service: Injected authentication service

    Returns:
        Authentication tokens and user information

    Raises:
        HTTPException: If authentication fails
    """
    try:
        # Create service login request
        service_login = ServiceLoginRequest(
            identifier=login_data.username,  # Can be username or email
            password=login_data.password,
        )
        
        # Authenticate user
        token_response = await auth_service.authenticate_user(service_login)
        return token_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    auth_service: AuthenticationService = Depends(get_auth_service),
):
    """Refresh access token using refresh token.

    Args:
        refresh_data: Refresh token request
        auth_service: Injected authentication service

    Returns:
        New authentication tokens

    Raises:
        HTTPException: If refresh token is invalid
    """
    try:
        # Create service refresh request
        service_refresh = ServiceRefreshTokenRequest(
            refresh_token=refresh_data.refresh_token
        )
        
        # Refresh token
        token_response = await auth_service.refresh_token(service_refresh)
        return token_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Logout user",
)
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthenticationService = Depends(get_auth_service),
):
    """Logout user by invalidating token.

    Args:
        credentials: Authorization credentials
        auth_service: Injected authentication service

    Returns:
        Logout confirmation message
    """
    try:
        # Get token from credentials
        token = credentials.credentials
        
        # Logout user
        success = await auth_service.logout_user(token)
        
        if success:
            return MessageResponse(
                message="Logged out successfully",
                success=True
            )
        else:
            return MessageResponse(
                message="Logout failed",
                success=False
            )
            
    except Exception as e:
        logger.error(f"Logout failed: {str(e)}")
        return MessageResponse(
            message="Logout failed",
            success=False
        )


@router.post(
    "/forgot-password",
    response_model=PasswordResetResponse,
    summary="Request password reset",
)
async def forgot_password(
    forgot_data: ForgotPasswordRequest,
    auth_service: AuthenticationService = Depends(get_auth_service),
):
    """Initiate password reset process.

    Args:
        forgot_data: Password reset request
        auth_service: Injected authentication service

    Returns:
        Password reset confirmation
    """
    try:
        # Create service password reset request
        service_reset = ServicePasswordResetRequest(
            email=forgot_data.email
        )
        
        # Initiate password reset
        await auth_service.initiate_password_reset(service_reset)
        
        # Always return success for security (don't reveal if email exists)
        return PasswordResetResponse(
            message="Password reset instructions sent to email",
            email=forgot_data.email,
        )
        
    except Exception as e:
        logger.error(f"Password reset request failed: {str(e)}")
        # Still return success for security
        return PasswordResetResponse(
            message="Password reset instructions sent to email",
            email=forgot_data.email,
        )


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Reset password with token",
)
async def reset_password(
    reset_data: ResetPasswordRequest,
    auth_service: AuthenticationService = Depends(get_auth_service),
):
    """Reset password using reset token.

    Args:
        reset_data: Password reset confirmation
        auth_service: Injected authentication service

    Returns:
        Password reset confirmation

    Raises:
        HTTPException: If reset token is invalid
    """
    try:
        # Create service password reset confirm request
        service_confirm = PasswordResetConfirmRequest(
            token=reset_data.token,
            new_password=reset_data.new_password,
        )
        
        # Confirm password reset
        success = await auth_service.confirm_password_reset(service_confirm)
        
        if success:
            return MessageResponse(
                message="Password reset successfully",
                success=True
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password reset failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset failed"
        )


@router.put(
    "/change-password",
    response_model=MessageResponse,
    summary="Change user password",
)
async def change_password(
    change_data: ChangePasswordRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthenticationService = Depends(get_auth_service),
    user_service: UserService = Depends(get_user_service),
):
    """Change authenticated user's password.

    Args:
        change_data: Password change request
        credentials: Authorization credentials
        auth_service: Injected authentication service
        user_service: Injected user service

    Returns:
        Password change confirmation

    Raises:
        HTTPException: If current password is incorrect
    """
    try:
        # Get current user from token
        token = credentials.credentials
        current_user = await auth_service.get_current_user(token)
        
        # Create password change request
        password_change = PasswordChangeRequest(
            current_password=change_data.current_password,
            new_password=change_data.new_password,
        )
        
        # Change password
        success = await user_service.change_password(
            current_user.id,
            password_change
        )
        
        if success:
            return MessageResponse(
                message="Password changed successfully",
                success=True
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to change password"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed"
        )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
)
async def get_me(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthenticationService = Depends(get_auth_service),
):
    """Get current authenticated user information.

    Args:
        credentials: Authorization credentials
        auth_service: Injected authentication service

    Returns:
        Current user information

    Raises:
        HTTPException: If token is invalid
    """
    try:
        # Get current user from token
        token = credentials.credentials
        user = await auth_service.get_current_user(token)
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get current user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


@router.put(
    "/profile",
    response_model=UserResponse,
    summary="Update user profile",
)
async def update_profile(
    update_data: Dict,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthenticationService = Depends(get_auth_service),
    user_service: UserService = Depends(get_user_service),
):
    """Update authenticated user's profile.

    Args:
        update_data: Profile update data
        credentials: Authorization credentials
        auth_service: Injected authentication service
        user_service: Injected user service

    Returns:
        Updated user information

    Raises:
        HTTPException: If update fails
    """
    try:
        # Get current user from token
        token = credentials.credentials
        current_user = await auth_service.get_current_user(token)
        
        # Create update request
        update_request = UserUpdateRequest(**update_data)
        
        # Update user profile
        updated_user = await user_service.update_user(current_user.id, update_request)
        return updated_user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Profile update failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Profile update failed"
        )


@router.post(
    "/verify-email",
    response_model=MessageResponse,
    summary="Verify email address",
)
async def verify_email(
    token: str = Query(..., description="Email verification token"),
    user_service: UserService = Depends(get_user_service),
):
    """Verify user's email address.

    Args:
        token: Email verification token
        user_service: Injected user service

    Returns:
        Verification confirmation

    Raises:
        HTTPException: If verification fails
    """
    try:
        # TODO: Implement email verification in UserService
        # For now, return a placeholder response
        logger.warning("Email verification not yet implemented")
        
        return MessageResponse(
            message="Email verification feature coming soon",
            success=False,
            details={"note": "Email verification not yet implemented"}
        )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email verification failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email verification failed"
        )


@router.post(
    "/resend-verification",
    response_model=MessageResponse,
    summary="Resend verification email",
)
async def resend_verification(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthenticationService = Depends(get_auth_service),
    user_service: UserService = Depends(get_user_service),
):
    """Resend email verification link.

    Args:
        credentials: Authorization credentials
        auth_service: Injected authentication service
        user_service: Injected user service

    Returns:
        Resend confirmation
    """
    try:
        # Get current user from token
        token = credentials.credentials
        current_user = await auth_service.get_current_user(token)
        
        # TODO: Implement resend verification email in UserService
        # For now, return a placeholder response
        logger.warning("Resend verification email not yet implemented")
        
        return MessageResponse(
            message="Email verification feature coming soon",
            success=False,
            details={"note": "Resend verification not yet implemented"}
        )
        
    except Exception as e:
        logger.error(f"Failed to resend verification: {str(e)}")
        return MessageResponse(
            message="Failed to send verification email",
            success=False
        )
