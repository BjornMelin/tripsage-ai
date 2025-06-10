"""User service for TripSage API.

This service acts as a thin wrapper around the core user service,
handling API-specific concerns like model adaptation and FastAPI integration.
"""

import logging
from typing import Optional

from fastapi import Depends
from pydantic import EmailStr

from tripsage.api.schemas.responses.auth import UserResponse
from tripsage_core.exceptions.exceptions import (
    CoreServiceError as ServiceError,
)
from tripsage_core.exceptions.exceptions import (
    CoreValidationError as ValidationError,
)
from tripsage_core.services.business.user_service import (
    UserService as CoreUserService,
)
from tripsage_core.services.business.user_service import (
    get_user_service as get_core_user_service,
)

logger = logging.getLogger(__name__)


class UserService:
    """
    API user service that delegates to core business services.

    This service acts as a façade, handling:
    - Model adaptation between API and core models
    - API-specific error handling
    - FastAPI dependency integration
    """

    def __init__(self, core_user_service: Optional[CoreUserService] = None):
        """
        Initialize the API user service.

        Args:
            core_user_service: Core user service
        """
        self.core_user_service = core_user_service

    async def _get_core_user_service(self) -> CoreUserService:
        """Get or create core user service instance."""
        if self.core_user_service is None:
            self.core_user_service = await get_core_user_service()
        return self.core_user_service

    async def get_user_by_id(self, user_id: str) -> Optional[UserResponse]:
        """Get a user by ID.

        Args:
            user_id: The user ID

        Returns:
            The user if found, None otherwise

        Raises:
            ServiceError: If retrieval fails
        """
        try:
            logger.info(f"Getting user by ID: {user_id}")

            # Get user via core service
            core_service = await self._get_core_user_service()
            core_user = await core_service.get_user_by_id(user_id)

            if core_user is None:
                return None

            # Adapt core response to API model
            return self._adapt_user_response(core_user)

        except Exception as e:
            logger.error(f"Failed to get user by ID: {str(e)}")
            raise ServiceError("Failed to get user") from e

    async def get_user_by_email(self, email: str) -> Optional[dict]:
        """Get a user by email.

        Args:
            email: The user email

        Returns:
            The user if found, None otherwise

        Raises:
            ServiceError: If retrieval fails
        """
        try:
            logger.info(f"Getting user by email: {email}")

            # Get user via core service
            core_service = await self._get_core_user_service()
            core_user = await core_service.get_user_by_email(email)

            return core_user

        except Exception as e:
            logger.error(f"Failed to get user by email: {str(e)}")
            raise ServiceError("Failed to get user") from e

    async def create_user(
        self, email: EmailStr, password: str, full_name: Optional[str] = None
    ) -> UserResponse:
        """Create a new user.

        Args:
            email: User email
            password: User password
            full_name: Optional user full name

        Returns:
            The created user

        Raises:
            ValidationError: If user data is invalid
            ServiceError: If creation fails
        """
        try:
            logger.info(f"Creating user with email: {email}")

            # Adapt API request to core model
            core_request = self._adapt_user_create_request(email, password, full_name)

            # Create user via core service
            core_service = await self._get_core_user_service()
            core_user = await core_service.create_user(core_request)

            # Adapt core response to API model
            return self._adapt_user_response(core_user)

        except (ValidationError, ServiceError) as e:
            logger.error(f"User creation failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating user: {str(e)}")
            raise ServiceError("Failed to create user") from e

    async def update_user(self, user_id: str, updates: dict) -> Optional[UserResponse]:
        """Update user information.

        Args:
            user_id: User ID
            updates: Fields to update

        Returns:
            Updated user if successful, None if user not found

        Raises:
            ValidationError: If update data is invalid
            ServiceError: If update fails
        """
        try:
            logger.info(f"Updating user {user_id}")

            # Update user via core service
            core_service = await self._get_core_user_service()
            core_user = await core_service.update_user(user_id, updates)

            if core_user is None:
                return None

            # Adapt core response to API model
            return self._adapt_user_response(core_user)

        except (ValidationError, ServiceError) as e:
            logger.error(f"User update failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error updating user: {str(e)}")
            raise ServiceError("Failed to update user") from e

    async def delete_user(self, user_id: str) -> bool:
        """Delete a user.

        Args:
            user_id: User ID

        Returns:
            True if deleted successfully

        Raises:
            ServiceError: If deletion fails
        """
        try:
            logger.info(f"Deleting user {user_id}")

            # Delete user via core service
            core_service = await self._get_core_user_service()
            return await core_service.delete_user(user_id)

        except Exception as e:
            logger.error(f"Failed to delete user: {str(e)}")
            raise ServiceError("Failed to delete user") from e

    async def change_password(
        self, user_id: str, current_password: str, new_password: str
    ) -> bool:
        """Change user password.

        Args:
            user_id: User ID
            current_password: Current password
            new_password: New password

        Returns:
            True if password changed successfully

        Raises:
            ValidationError: If passwords are invalid
            ServiceError: If change fails
        """
        try:
            logger.info(f"Changing password for user {user_id}")

            # Change password via core service
            core_service = await self._get_core_user_service()
            return await core_service.change_password(
                user_id, current_password, new_password
            )

        except (ValidationError, ServiceError) as e:
            logger.error(f"Password change failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error changing password: {str(e)}")
            raise ServiceError("Failed to change password") from e

    async def verify_password(self, user_id: str, password: str) -> bool:
        """Verify user password.

        Args:
            user_id: User ID
            password: Password to verify

        Returns:
            True if password is correct

        Raises:
            ServiceError: If verification fails
        """
        try:
            logger.info(f"Verifying password for user {user_id}")

            # Verify password via core service
            core_service = await self._get_core_user_service()
            return await core_service.verify_password(user_id, password)

        except Exception as e:
            logger.error(f"Password verification failed: {str(e)}")
            raise ServiceError("Failed to verify password") from e

    def _adapt_user_create_request(
        self, email: EmailStr, password: str, full_name: Optional[str]
    ) -> dict:
        """Adapt user creation parameters to core model."""
        return {
            "email": str(email),
            "password": password,
            "full_name": full_name,
        }

    def _adapt_user_response(self, core_user) -> UserResponse:
        """Adapt core user response to API model."""
        return UserResponse(
            id=core_user.get("id", ""),
            email=core_user.get("email", ""),
            full_name=core_user.get("full_name"),
            is_active=core_user.get("is_active", True),
            is_verified=core_user.get("is_verified", False),
            created_at=core_user.get("created_at", ""),
            updated_at=core_user.get("updated_at", ""),
            preferences=core_user.get("preferences", {}),
        )


# Module-level dependency annotation
_core_user_service_dep = Depends(get_core_user_service)


# Dependency function for FastAPI
async def get_user_service(
    core_user_service: CoreUserService = _core_user_service_dep,
) -> UserService:
    """
    Get user service instance for dependency injection.

    Args:
        core_user_service: Core user service

    Returns:
        UserService instance
    """
    return UserService(core_user_service=core_user_service)
