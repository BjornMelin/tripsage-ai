"""Auth service for TripSage API.

This service acts as a thin wrapper around the core auth service,
handling API-specific concerns like model adaptation and FastAPI integration.
"""

import logging
from typing import Optional

from fastapi import Depends

from tripsage.api.schemas.requests.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    ResetPasswordRequest,
)
from tripsage.api.schemas.responses.auth import (
    AuthResponse,
    MessageResponse,
    TokenResponse,
    UserResponse,
)
from tripsage_core.exceptions.exceptions import (
    CoreAuthenticationError as AuthenticationError,
)
from tripsage_core.exceptions.exceptions import (
    CoreServiceError as ServiceError,
)
from tripsage_core.exceptions.exceptions import (
    CoreValidationError as ValidationError,
)
from tripsage_core.services.business.auth_service import (
    AuthenticationService as CoreAuthService,
)
from tripsage_core.services.business.auth_service import (
    get_auth_service as get_core_auth_service,
)

logger = logging.getLogger(__name__)


class AuthService:
    """
    API auth service that delegates to core business services.

    This service acts as a façade, handling:
    - Model adaptation between API and core models
    - API-specific error handling
    - FastAPI dependency integration
    """

    def __init__(self, core_auth_service: Optional[CoreAuthService] = None):
        """
        Initialize the API auth service.

        Args:
            core_auth_service: Core auth service
        """
        self.core_auth_service = core_auth_service

    async def _get_core_auth_service(self) -> CoreAuthService:
        """Get or create core auth service instance."""
        if self.core_auth_service is None:
            self.core_auth_service = await get_core_auth_service()
        return self.core_auth_service

    async def register_user(self, request: RegisterRequest) -> AuthResponse:
        """Register a new user.

        Args:
            request: User registration request

        Returns:
            Authentication response with user and tokens

        Raises:
            ValidationError: If user data is invalid
            ServiceError: If registration fails
        """
        try:
            logger.info(f"Registering user with email: {request.email}")

            # Adapt API request to core model
            core_request = self._adapt_register_request(request)

            # Register user via core service
            core_service = await self._get_core_auth_service()
            core_response = await core_service.register_user(core_request)

            # Adapt core response to API model
            return self._adapt_auth_response(core_response)

        except (ValidationError, ServiceError, AuthenticationError) as e:
            logger.error(f"User registration failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error registering user: {str(e)}")
            raise ServiceError("Registration failed") from e

    async def login_user(self, request: LoginRequest) -> AuthResponse:
        """Login a user.

        Args:
            request: User login request

        Returns:
            Authentication response with user and tokens

        Raises:
            AuthenticationError: If credentials are invalid
            ServiceError: If login fails
        """
        try:
            logger.info(f"Attempting login for user: {request.username}")

            # Adapt API request to core model
            core_request = self._adapt_login_request(request)

            # Login via core service
            core_service = await self._get_core_auth_service()
            core_response = await core_service.login_user(core_request)

            # Adapt core response to API model
            return self._adapt_auth_response(core_response)

        except (AuthenticationError, ServiceError) as e:
            logger.error(f"User login failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during login: {str(e)}")
            raise ServiceError("Login failed") from e

    async def refresh_token(self, request: RefreshTokenRequest) -> TokenResponse:
        """Refresh an access token.

        Args:
            request: Refresh token request

        Returns:
            New token response

        Raises:
            AuthenticationError: If refresh token is invalid
            ServiceError: If refresh fails
        """
        try:
            logger.info("Refreshing access token")

            # Refresh token via core service
            core_service = await self._get_core_auth_service()
            core_response = await core_service.refresh_token(request.refresh_token)

            # Adapt core response to API model
            return self._adapt_token_response(core_response)

        except (AuthenticationError, ServiceError) as e:
            logger.error(f"Token refresh failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error refreshing token: {str(e)}")
            raise ServiceError("Token refresh failed") from e

    async def logout_user(self, user_id: str, token: str) -> MessageResponse:
        """Logout a user.

        Args:
            user_id: User ID
            token: Access token to invalidate

        Returns:
            Success message

        Raises:
            ServiceError: If logout fails
        """
        try:
            logger.info(f"Logging out user: {user_id}")

            # Logout via core service
            core_service = await self._get_core_auth_service()
            await core_service.logout_user(user_id, token)

            return MessageResponse(message="Successfully logged out")

        except Exception as e:
            logger.error(f"Logout failed: {str(e)}")
            raise ServiceError("Logout failed") from e

    async def change_password(
        self, user_id: str, request: ChangePasswordRequest
    ) -> MessageResponse:
        """Change user password.

        Args:
            user_id: User ID
            request: Change password request

        Returns:
            Success message

        Raises:
            ValidationError: If passwords are invalid
            AuthenticationError: If current password is wrong
            ServiceError: If change fails
        """
        try:
            logger.info(f"Changing password for user: {user_id}")

            # Change password via core service
            core_service = await self._get_core_auth_service()
            await core_service.change_password(
                user_id, request.current_password, request.new_password
            )

            return MessageResponse(message="Password changed successfully")

        except (ValidationError, AuthenticationError, ServiceError) as e:
            logger.error(f"Password change failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error changing password: {str(e)}")
            raise ServiceError("Password change failed") from e

    async def forgot_password(self, request: ForgotPasswordRequest) -> MessageResponse:
        """Initiate password reset process.

        Args:
            request: Forgot password request

        Returns:
            Success message

        Raises:
            ServiceError: If request fails
        """
        try:
            logger.info(f"Password reset requested for email: {request.email}")

            # Request password reset via core service
            core_service = await self._get_core_auth_service()
            await core_service.forgot_password(request.email)

            return MessageResponse(
                message=(
                    "If the email exists, password reset instructions have been sent"
                )
            )

        except Exception as e:
            logger.error(f"Password reset request failed: {str(e)}")
            raise ServiceError("Password reset request failed") from e

    async def reset_password(self, request: ResetPasswordRequest) -> MessageResponse:
        """Reset user password with token.

        Args:
            request: Reset password request

        Returns:
            Success message

        Raises:
            ValidationError: If token or password is invalid
            ServiceError: If reset fails
        """
        try:
            logger.info("Resetting password with token")

            # Reset password via core service
            core_service = await self._get_core_auth_service()
            await core_service.reset_password(request.token, request.new_password)

            return MessageResponse(message="Password reset successfully")

        except (ValidationError, ServiceError) as e:
            logger.error(f"Password reset failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error resetting password: {str(e)}")
            raise ServiceError("Password reset failed") from e

    async def verify_token(self, token: str) -> Optional[dict]:
        """Verify and decode a JWT token.

        Args:
            token: JWT token to verify

        Returns:
            Token payload if valid, None otherwise

        Raises:
            AuthenticationError: If token is invalid
            ServiceError: If verification fails
        """
        try:
            logger.debug("Verifying JWT token")

            # Verify token via core service
            core_service = await self._get_core_auth_service()
            return await core_service.verify_token(token)

        except AuthenticationError as e:
            logger.error(f"Token verification failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error verifying token: {str(e)}")
            raise ServiceError("Token verification failed") from e

    def _adapt_register_request(self, request: RegisterRequest) -> dict:
        """Adapt register request to core model."""
        return {
            "username": request.username,
            "email": request.email,
            "password": request.password,
            "full_name": request.full_name,
        }

    def _adapt_login_request(self, request: LoginRequest) -> dict:
        """Adapt login request to core model."""
        return {
            "identifier": request.username,
            "password": request.password,
            "remember_me": request.remember_me,
        }

    def _adapt_auth_response(self, core_response) -> AuthResponse:
        """Adapt core auth response to API model."""
        return AuthResponse(
            user=UserResponse(
                id=core_response.get("user", {}).get("id", ""),
                username=core_response.get("user", {}).get("username", ""),
                email=core_response.get("user", {}).get("email", ""),
                full_name=core_response.get("user", {}).get("full_name"),
                is_active=core_response.get("user", {}).get("is_active", True),
                is_verified=core_response.get("user", {}).get("is_verified", False),
                created_at=core_response.get("user", {}).get("created_at", ""),
                updated_at=core_response.get("user", {}).get("updated_at", ""),
                preferences=core_response.get("user", {}).get("preferences", {}),
            ),
            tokens=TokenResponse(
                access_token=core_response.get("tokens", {}).get("access_token", ""),
                refresh_token=core_response.get("tokens", {}).get("refresh_token", ""),
                token_type=core_response.get("tokens", {}).get("token_type", "bearer"),
                expires_in=core_response.get("tokens", {}).get("expires_in", 3600),
            ),
        )

    def _adapt_token_response(self, core_response) -> TokenResponse:
        """Adapt core token response to API model."""
        return TokenResponse(
            access_token=core_response.get("access_token", ""),
            refresh_token=core_response.get("refresh_token", ""),
            token_type=core_response.get("token_type", "bearer"),
            expires_in=core_response.get("expires_in", 3600),
        )


# Module-level dependency annotation
_core_auth_service_dep = Depends(get_core_auth_service)


# Dependency function for FastAPI
async def get_auth_service(
    core_auth_service: CoreAuthService = _core_auth_service_dep,
) -> AuthService:
    """
    Get auth service instance for dependency injection.

    Args:
        core_auth_service: Core auth service

    Returns:
        AuthService instance
    """
    return AuthService(core_auth_service=core_auth_service)
