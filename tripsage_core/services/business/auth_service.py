"""
Authentication service for JWT token management and user authentication.

This service consolidates authentication logic including token generation,
validation, refresh operations, and user session management. It depends on
the user service for user operations and follows clean architecture principles.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from pydantic import Field

from tripsage_core.exceptions import (
    CoreAuthenticationError as AuthenticationError,
)
from tripsage_core.models.base_core_model import TripSageModel
from tripsage_core.services.business.user_service import UserResponse, UserService

logger = logging.getLogger(__name__)


class TokenData(TripSageModel):
    """Token payload data structure."""

    sub: str = Field(..., description="Subject (user ID)")
    exp: int = Field(..., description="Expiration timestamp")
    iat: int = Field(..., description="Issued at timestamp")
    user_id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    token_type: str = Field(..., description="Token type (access/refresh)")
    jti: Optional[str] = Field(None, description="JWT ID for revocation")


class LoginRequest(TripSageModel):
    """Request model for user login."""

    identifier: str = Field(..., description="Email or username")
    password: str = Field(..., description="Password")


class TokenResponse(TripSageModel):
    """Response model for authentication tokens."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")
    user: UserResponse = Field(..., description="User information")


class RefreshTokenRequest(TripSageModel):
    """Request model for token refresh."""

    refresh_token: str = Field(..., description="Refresh token")


class PasswordResetRequest(TripSageModel):
    """Request model for password reset initiation."""

    email: str = Field(..., description="User email")


class PasswordResetConfirmRequest(TripSageModel):
    """Request model for password reset confirmation."""

    token: str = Field(..., description="Reset token")
    new_password: str = Field(..., min_length=8, description="New password")


class AuthenticationService:
    """
    Comprehensive authentication service.

    This service handles:
    - User login and logout
    - JWT token generation and validation
    - Token refresh operations
    - Password reset workflows
    - Session management

    Dependencies are injected for better testability and loose coupling.
    """

    def __init__(
        self,
        user_service: Optional[UserService] = None,
        secret_key: Optional[str] = None,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 30,
        refresh_token_expire_days: int = 7,
    ):
        """
        Initialize the authentication service.

        Args:
            user_service: User service for user operations
            secret_key: JWT signing secret key
            algorithm: JWT signing algorithm
            access_token_expire_minutes: Access token expiration time
            refresh_token_expire_days: Refresh token expiration time
        """
        # Import here to avoid circular imports
        if user_service is None:
            user_service = UserService()

        if secret_key is None:
            # Get from settings
            from tripsage_core.config.base_app_settings import get_settings

            settings = get_settings()
            secret_key = settings.jwt_secret_key

        self.user_service = user_service
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days

    async def authenticate_user(self, login_data: LoginRequest) -> TokenResponse:
        """
        Authenticate user and generate tokens.

        Args:
            login_data: Login credentials

        Returns:
            Authentication tokens and user information

        Raises:
            AuthenticationError: If authentication fails
        """
        try:
            # Verify user credentials
            user = await self.user_service.verify_user_credentials(
                login_data.identifier, login_data.password
            )

            if not user:
                raise AuthenticationError("Invalid credentials")

            # Generate tokens
            access_token = await self._create_access_token(user)
            refresh_token = await self._create_refresh_token(user)

            logger.info(
                "User authenticated successfully",
                extra={"user_id": user.id, "email": user.email},
            )

            return TokenResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=self.access_token_expire_minutes * 60,
                user=user,
            )

        except AuthenticationError:
            raise
        except Exception as e:
            logger.error(
                "Authentication failed",
                extra={"identifier": login_data.identifier, "error": str(e)},
            )
            raise AuthenticationError("Authentication failed") from e

    async def refresh_token(
        self, refresh_request: RefreshTokenRequest
    ) -> TokenResponse:
        """
        Refresh access token using refresh token.

        Args:
            refresh_request: Refresh token request

        Returns:
            New authentication tokens

        Raises:
            AuthenticationError: If refresh token is invalid
        """
        try:
            # Validate refresh token
            token_data = await self._validate_token(
                refresh_request.refresh_token, expected_type="refresh"
            )

            # Get current user information
            user = await self.user_service.get_user_by_id(token_data.user_id)
            if not user or not user.is_active:
                raise AuthenticationError("User not found or inactive")

            # Generate new tokens
            access_token = await self._create_access_token(user)
            new_refresh_token = await self._create_refresh_token(user)

            logger.info("Token refreshed successfully", extra={"user_id": user.id})

            return TokenResponse(
                access_token=access_token,
                refresh_token=new_refresh_token,
                expires_in=self.access_token_expire_minutes * 60,
                user=user,
            )

        except AuthenticationError:
            raise
        except Exception as e:
            logger.error("Token refresh failed", extra={"error": str(e)})
            raise AuthenticationError("Token refresh failed") from e

    async def validate_access_token(self, token: str) -> TokenData:
        """
        Validate access token and return token data.

        Args:
            token: JWT access token

        Returns:
            Token data

        Raises:
            AuthenticationError: If token is invalid
        """
        return await self._validate_token(token, expected_type="access")

    async def get_current_user(self, token: str) -> UserResponse:
        """
        Get current user from access token.

        Args:
            token: JWT access token

        Returns:
            Current user information

        Raises:
            AuthenticationError: If token is invalid or user not found
        """
        try:
            # Validate token
            token_data = await self.validate_access_token(token)

            # Get user
            user = await self.user_service.get_user_by_id(token_data.user_id)
            if not user or not user.is_active:
                raise AuthenticationError("User not found or inactive")

            return user

        except AuthenticationError:
            raise
        except Exception as e:
            logger.error("Failed to get current user", extra={"error": str(e)})
            raise AuthenticationError("Invalid token") from e

    async def initiate_password_reset(
        self, reset_request: PasswordResetRequest
    ) -> bool:
        """
        Initiate password reset process.

        Args:
            reset_request: Password reset request

        Returns:
            True if reset email sent (always returns True for security)
        """
        try:
            # Check if user exists
            user = await self.user_service.get_user_by_email(reset_request.email)
            if not user:
                # Don't reveal if email exists for security
                logger.warning(
                    "Password reset requested for non-existent email",
                    extra={"email": reset_request.email},
                )
                return True

            # Generate reset token
            reset_token = await self._create_password_reset_token(user)

            # TODO: Send reset email
            # This would integrate with an email service
            logger.info(
                "Password reset initiated",
                extra={
                    "user_id": user.id,
                    "email": user.email,
                    "reset_token": reset_token,  # Remove in production
                },
            )

            return True

        except Exception as e:
            logger.error(
                "Failed to initiate password reset",
                extra={"email": reset_request.email, "error": str(e)},
            )
            return True  # Don't reveal errors for security

    async def confirm_password_reset(
        self, confirm_request: PasswordResetConfirmRequest
    ) -> bool:
        """
        Confirm password reset with token.

        Args:
            confirm_request: Password reset confirmation

        Returns:
            True if password reset successful

        Raises:
            AuthenticationError: If reset token is invalid
            ValidationError: If new password is invalid
        """
        try:
            # Validate reset token
            token_data = await self._validate_token(
                confirm_request.token, expected_type="password_reset"
            )

            # Get user
            user = await self.user_service.get_user_by_id(token_data.user_id)
            if not user:
                raise AuthenticationError("Invalid reset token")

            # Update password directly in database
            # We bypass the current password check for reset operations

            # Create a special password change request that bypasses current password
            success = await self._reset_user_password(
                user.id, confirm_request.new_password
            )

            if success:
                logger.info("Password reset completed", extra={"user_id": user.id})

            return success

        except AuthenticationError:
            raise
        except Exception as e:
            logger.error("Password reset confirmation failed", extra={"error": str(e)})
            raise AuthenticationError("Password reset failed") from e

    async def logout_user(self, token: str) -> bool:
        """
        Logout user by invalidating token.

        Note: In a stateless JWT system, this would typically involve
        token blacklisting or shorter token expiration times.

        Args:
            token: Access token to invalidate

        Returns:
            True if logout successful
        """
        try:
            # Validate token first
            token_data = await self.validate_access_token(token)

            # TODO: Add token to blacklist if implementing token revocation
            # For now, we just log the logout
            logger.info("User logged out", extra={"user_id": token_data.user_id})

            return True

        except Exception as e:
            logger.error("Logout failed", extra={"error": str(e)})
            return False

    async def _create_access_token(self, user: UserResponse) -> str:
        """
        Create JWT access token.

        Args:
            user: User information

        Returns:
            JWT access token
        """
        now = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=self.access_token_expire_minutes)

        token_data = {
            "sub": user.id,
            "user_id": user.id,
            "email": user.email,
            "token_type": "access",
            "iat": int(now.timestamp()),
            "exp": int(expire.timestamp()),
        }

        return jwt.encode(token_data, self.secret_key, algorithm=self.algorithm)

    async def _create_refresh_token(self, user: UserResponse) -> str:
        """
        Create JWT refresh token.

        Args:
            user: User information

        Returns:
            JWT refresh token
        """
        now = datetime.now(timezone.utc)
        expire = now + timedelta(days=self.refresh_token_expire_days)

        token_data = {
            "sub": user.id,
            "user_id": user.id,
            "email": user.email,
            "token_type": "refresh",
            "iat": int(now.timestamp()),
            "exp": int(expire.timestamp()),
        }

        return jwt.encode(token_data, self.secret_key, algorithm=self.algorithm)

    async def _create_password_reset_token(self, user: UserResponse) -> str:
        """
        Create password reset token.

        Args:
            user: User information

        Returns:
            Password reset token
        """
        now = datetime.now(timezone.utc)
        expire = now + timedelta(hours=1)  # Reset tokens expire in 1 hour

        token_data = {
            "sub": user.id,
            "user_id": user.id,
            "email": user.email,
            "token_type": "password_reset",
            "iat": int(now.timestamp()),
            "exp": int(expire.timestamp()),
        }

        return jwt.encode(token_data, self.secret_key, algorithm=self.algorithm)

    async def _validate_token(self, token: str, expected_type: str) -> TokenData:
        """
        Validate JWT token and return token data.

        Args:
            token: JWT token
            expected_type: Expected token type

        Returns:
            Token data

        Raises:
            AuthenticationError: If token is invalid
        """
        try:
            # Decode token
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

            # Validate token type
            if payload.get("token_type") != expected_type:
                raise AuthenticationError(
                    f"Invalid token type, expected {expected_type}"
                )

            # Check expiration
            now = datetime.now(timezone.utc).timestamp()
            if payload.get("exp", 0) < now:
                raise AuthenticationError("Token has expired")

            # Return token data
            return TokenData(**payload)

        except jwt.ExpiredSignatureError as e:
            raise AuthenticationError("Token has expired") from e
        except jwt.InvalidTokenError as e:
            raise AuthenticationError(f"Invalid token: {str(e)}") from e
        except Exception as e:
            raise AuthenticationError(f"Token validation failed: {str(e)}") from e

    async def _reset_user_password(self, user_id: str, new_password: str) -> bool:
        """
        Reset user password without current password verification.

        Args:
            user_id: User ID
            new_password: New password

        Returns:
            True if successful
        """
        try:
            # Hash new password
            from tripsage_core.services.business.user_service import pwd_context

            hashed_password = pwd_context.hash(new_password)

            # Update password in database
            from tripsage_core.services.infrastructure import get_database_service

            db = get_database_service()
            success = await db.update_user_password(user_id, hashed_password)

            return success

        except Exception as e:
            logger.error(
                "Failed to reset password", extra={"user_id": user_id, "error": str(e)}
            )
            return False


# Dependency function for FastAPI
async def get_auth_service() -> AuthenticationService:
    """
    Get authentication service instance for dependency injection.

    Returns:
        AuthenticationService instance
    """
    from tripsage_core.services.infrastructure.database_service import get_database_service
    from tripsage_core.services.business.user_service import UserService
    
    database_service = await get_database_service()
    user_service = UserService(database_service=database_service)
    return AuthenticationService(user_service=user_service)
