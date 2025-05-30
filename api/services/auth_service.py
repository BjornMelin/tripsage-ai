"""
Authentication service for the TripSage API.

This service acts as a thin wrapper around the core authentication service,
handling API-specific concerns like model adaptation and FastAPI integration.
"""

import logging
from typing import Optional

from fastapi import Depends

from api.schemas.requests.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RefreshTokenRequest,
    RegisterUserRequest,
    ResetPasswordRequest,
)
from api.schemas.responses.auth import (
    MessageResponse,
    PasswordResetResponse,
    TokenResponse,
    UserResponse,
)
from tripsage_core.exceptions.exceptions import (
    CoreAuthenticationError as AuthenticationError,
)
from tripsage_core.services.business.auth_service import (
    AuthenticationService as CoreAuthService,
)
from tripsage_core.services.business.auth_service import (
    LoginRequest as CoreLoginRequest,
)
from tripsage_core.services.business.auth_service import (
    PasswordResetConfirmRequest as CorePasswordResetConfirmRequest,
)
from tripsage_core.services.business.auth_service import (
    PasswordResetRequest as CorePasswordResetRequest,
)
from tripsage_core.services.business.auth_service import (
    RefreshTokenRequest as CoreRefreshTokenRequest,
)
from tripsage_core.services.business.auth_service import (
    get_auth_service as get_core_auth_service,
)
from tripsage_core.services.business.user_service import (
    UserCreateRequest,
    UserService,
    get_user_service,
)

logger = logging.getLogger(__name__)


class AuthService:
    """
    API authentication service that delegates to core business services.

    This service acts as a façade, handling:
    - Model adaptation between API and core models
    - API-specific error handling
    - FastAPI dependency integration
    """

    def __init__(
        self,
        core_auth_service: Optional[CoreAuthService] = None,
        user_service: Optional[UserService] = None,
    ):
        """
        Initialize the API auth service.

        Args:
            core_auth_service: Core authentication service
            user_service: Core user service
        """
        self.core_auth_service = core_auth_service
        self.user_service = user_service

    async def _get_core_auth_service(self) -> CoreAuthService:
        """Get or create core auth service instance."""
        if self.core_auth_service is None:
            self.core_auth_service = await get_core_auth_service()
        return self.core_auth_service

    async def _get_user_service(self) -> UserService:
        """Get or create user service instance."""
        if self.user_service is None:
            self.user_service = await get_user_service()
        return self.user_service

    async def register_user(self, request: RegisterUserRequest) -> TokenResponse:
        """
        Register a new user.

        Args:
            request: User registration request

        Returns:
            Authentication tokens and user information

        Raises:
            AuthenticationError: If registration fails
        """
        try:
            # Adapt API request to core model
            core_request = UserCreateRequest(
                username=request.username,
                email=request.email,
                password=request.password,
                full_name=request.full_name,
            )

            # Create user via core service
            user_service = await self._get_user_service()
            await user_service.create_user(core_request)

            # Authenticate the newly created user
            login_request = CoreLoginRequest(
                identifier=request.username,
                password=request.password,
            )

            core_auth_service = await self._get_core_auth_service()
            token_response = await core_auth_service.authenticate_user(login_request)

            # Adapt core response to API model
            return self._adapt_token_response(token_response)

        except Exception as e:
            logger.error(f"User registration failed: {str(e)}")
            raise AuthenticationError("Registration failed") from e

    async def login_user(self, request: LoginRequest) -> TokenResponse:
        """
        Authenticate user and generate tokens.

        Args:
            request: Login request

        Returns:
            Authentication tokens and user information

        Raises:
            AuthenticationError: If authentication fails
        """
        try:
            # Adapt API request to core model
            core_request = CoreLoginRequest(
                identifier=request.username,
                password=request.password,
            )

            # Authenticate via core service
            core_auth_service = await self._get_core_auth_service()
            token_response = await core_auth_service.authenticate_user(core_request)

            # Adapt core response to API model
            return self._adapt_token_response(token_response)

        except Exception as e:
            logger.error(f"User login failed: {str(e)}")
            raise AuthenticationError("Authentication failed") from e

    async def refresh_token(self, request: RefreshTokenRequest) -> TokenResponse:
        """
        Refresh access token using refresh token.

        Args:
            request: Token refresh request

        Returns:
            New authentication tokens

        Raises:
            AuthenticationError: If refresh fails
        """
        try:
            # Adapt API request to core model
            core_request = CoreRefreshTokenRequest(refresh_token=request.refresh_token)

            # Refresh via core service
            core_auth_service = await self._get_core_auth_service()
            token_response = await core_auth_service.refresh_token(core_request)

            # Adapt core response to API model
            return self._adapt_token_response(token_response)

        except Exception as e:
            logger.error(f"Token refresh failed: {str(e)}")
            raise AuthenticationError("Token refresh failed") from e

    async def get_current_user(self, token: str) -> UserResponse:
        """
        Get current user from access token.

        Args:
            token: JWT access token

        Returns:
            Current user information

        Raises:
            AuthenticationError: If token is invalid
        """
        try:
            # Get user via core service
            core_auth_service = await self._get_core_auth_service()
            user = await core_auth_service.get_current_user(token)

            # Adapt core response to API model
            return self._adapt_user_response(user)

        except Exception as e:
            logger.error(f"Failed to get current user: {str(e)}")
            raise AuthenticationError("Invalid token") from e

    async def change_password(
        self, user_id: str, request: ChangePasswordRequest
    ) -> MessageResponse:
        """
        Change user password.

        Args:
            user_id: User ID
            request: Password change request

        Returns:
            Success message

        Raises:
            AuthenticationError: If password change fails
        """
        try:
            # Change password via core service
            user_service = await self._get_user_service()
            success = await user_service.change_password(
                user_id=user_id,
                current_password=request.current_password,
                new_password=request.new_password,
            )

            if not success:
                raise AuthenticationError("Password change failed")

            return MessageResponse(
                message="Password changed successfully",
                success=True,
            )

        except Exception as e:
            logger.error(f"Password change failed: {str(e)}")
            raise AuthenticationError("Password change failed") from e

    async def forgot_password(
        self, request: ForgotPasswordRequest
    ) -> PasswordResetResponse:
        """
        Initiate password reset process.

        Args:
            request: Forgot password request

        Returns:
            Password reset response
        """
        try:
            # Adapt API request to core model
            core_request = CorePasswordResetRequest(email=request.email)

            # Initiate reset via core service
            core_auth_service = await self._get_core_auth_service()
            await core_auth_service.initiate_password_reset(core_request)

            # Always return success for security (don't reveal if email exists)
            return PasswordResetResponse(
                message="If the email exists, a password reset link has been sent",
                email=request.email,
                success=True,
            )

        except Exception as e:
            logger.error(f"Password reset initiation failed: {str(e)}")
            # Still return success for security
            return PasswordResetResponse(
                message="If the email exists, a password reset link has been sent",
                email=request.email,
                success=True,
            )

    async def reset_password(self, request: ResetPasswordRequest) -> MessageResponse:
        """
        Reset password using reset token.

        Args:
            request: Password reset request

        Returns:
            Success message

        Raises:
            AuthenticationError: If reset fails
        """
        try:
            # Adapt API request to core model
            core_request = CorePasswordResetConfirmRequest(
                token=request.token,
                new_password=request.new_password,
            )

            # Reset password via core service
            core_auth_service = await self._get_core_auth_service()
            success = await core_auth_service.confirm_password_reset(core_request)

            if not success:
                raise AuthenticationError("Password reset failed")

            return MessageResponse(
                message="Password reset successfully",
                success=True,
            )

        except Exception as e:
            logger.error(f"Password reset failed: {str(e)}")
            raise AuthenticationError("Password reset failed") from e

    async def logout_user(self, token: str) -> MessageResponse:
        """
        Logout user by invalidating token.

        Args:
            token: Access token to invalidate

        Returns:
            Success message
        """
        try:
            # Logout via core service
            core_auth_service = await self._get_core_auth_service()
            success = await core_auth_service.logout_user(token)

            return MessageResponse(
                message="Logged out successfully",
                success=success,
            )

        except Exception as e:
            logger.error(f"Logout failed: {str(e)}")
            return MessageResponse(
                message="Logout completed",
                success=True,  # Always return success for logout
            )

    def _adapt_token_response(self, core_response) -> TokenResponse:
        """
        Adapt core token response to API model.

        Args:
            core_response: Core token response

        Returns:
            API token response
        """
        return TokenResponse(
            access_token=core_response.access_token,
            refresh_token=core_response.refresh_token,
            token_type=core_response.token_type,
            expires_in=core_response.expires_in,
        )

    def _adapt_user_response(self, core_user) -> UserResponse:
        """
        Adapt core user response to API model.

        Args:
            core_user: Core user response

        Returns:
            API user response
        """
        return UserResponse(
            id=core_user.id,
            username=core_user.username,
            email=core_user.email,
            full_name=core_user.full_name,
            is_active=core_user.is_active,
            is_verified=core_user.is_verified,
            created_at=core_user.created_at,
            updated_at=core_user.updated_at,
            preferences=core_user.preferences,
        )


# Module-level dependency annotations
_core_auth_service_dep = Depends(get_core_auth_service)
_user_service_dep = Depends(get_user_service)


# Dependency function for FastAPI
async def get_auth_service(
    core_auth_service: CoreAuthService = _core_auth_service_dep,
    user_service: UserService = _user_service_dep,
) -> AuthService:
    """
    Get auth service instance for dependency injection.

    Args:
        core_auth_service: Core authentication service
        user_service: Core user service

    Returns:
        AuthService instance
    """
    return AuthService(
        core_auth_service=core_auth_service,
        user_service=user_service,
    )
