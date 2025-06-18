"""
User service for comprehensive user management operations.

This service consolidates user-related business logic including user creation,
retrieval, updates, and password management. It follows clean architecture
principles with proper dependency injection and error handling.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from passlib.context import CryptContext
from pydantic import EmailStr, Field, field_validator

from tripsage_core.exceptions import (
    CoreAuthenticationError as AuthenticationError,
)
from tripsage_core.exceptions import (
    CoreResourceNotFoundError as NotFoundError,
)
from tripsage_core.exceptions import (
    CoreValidationError as ValidationError,
)
from tripsage_core.models.base_core_model import TripSageModel

logger = logging.getLogger(__name__)

# Password hashing context with modern settings
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,  # Higher rounds for better security
)

class UserCreateRequest(TripSageModel):
    """Request model for user creation."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")
    full_name: str | None = Field(None, max_length=100, description="Full name")
    username: str | None = Field(
        None, min_length=3, max_length=30, description="Username"
    )

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")

        # Check for at least one digit, one letter
        has_digit = any(c.isdigit() for c in v)
        has_letter = any(c.isalpha() for c in v)

        if not (has_digit and has_letter):
            raise ValueError("Password must contain at least one letter and one digit")

        return v

class UserUpdateRequest(TripSageModel):
    """Request model for user updates."""

    full_name: str | None = Field(None, max_length=100)
    username: str | None = Field(None, min_length=3, max_length=30)
    preferences: dict[str, Any] | None = Field(None)
    is_active: bool | None = Field(None)

class UserResponse(TripSageModel):
    """Response model for user data."""

    id: str = Field(..., description="User ID")
    email: EmailStr = Field(..., description="User email")
    full_name: str | None = Field(None, description="Full name")
    username: str | None = Field(None, description="Username")
    is_active: bool = Field(True, description="User active status")
    is_verified: bool = Field(False, description="Email verification status")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    preferences: dict[str, Any] = Field(
        default_factory=dict, description="User preferences"
    )

class PasswordChangeRequest(TripSageModel):
    """Request model for password changes."""

    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        """Validate new password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")

        has_digit = any(c.isdigit() for c in v)
        has_letter = any(c.isalpha() for c in v)

        if not (has_digit and has_letter):
            raise ValueError("Password must contain at least one letter and one digit")

        return v

class UserService:
    """
    Comprehensive user management service.

    This service handles all user-related operations including:
    - User creation and registration
    - User retrieval and search
    - Password management and hashing
    - User updates and preferences
    - Account activation/deactivation

    Dependencies are injected via constructor for better testability.
    """

    def __init__(self, database_service=None):
        """
        Initialize the user service.

        Args:
            database_service: Database service for data persistence
        """
        if database_service is None:
            # For now, we'll require database service to be injected
            # In production, this would be provided by the dependency injection system
            raise ValueError(
                "database_service is required for UserService initialization"
            )

        self.db = database_service
        self._pwd_context = pwd_context

    async def create_user(self, user_data: UserCreateRequest) -> UserResponse:
        """
        Create a new user account.

        Args:
            user_data: User creation data

        Returns:
            Created user information

        Raises:
            ValidationError: If user data is invalid or email already exists
        """
        try:
            # Check if user already exists
            existing_user = await self.get_user_by_email(user_data.email)
            if existing_user:
                raise ValidationError(
                    f"User with email {user_data.email} already exists"
                )

            # Check username uniqueness if provided
            if user_data.username:
                existing_username = await self.get_user_by_username(user_data.username)
                if existing_username:
                    raise ValidationError(
                        f"Username {user_data.username} already taken"
                    )

            # Generate user ID and hash password
            user_id = str(uuid.uuid4())
            hashed_password = self._hash_password(user_data.password)

            # Prepare user data for database
            now = datetime.now(timezone.utc)
            db_user_data = {
                "id": user_id,
                "email": str(user_data.email),
                "hashed_password": hashed_password,
                "full_name": user_data.full_name,
                "username": user_data.username,
                "is_active": True,
                "is_verified": False,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
                "preferences": {},
            }

            # Store in database
            result = await self.db.create_user(db_user_data)

            logger.info(
                "User created successfully",
                extra={"user_id": user_id, "email": str(user_data.email)},
            )

            # Return user response (excluding password)
            return UserResponse(
                id=result["id"],
                email=result["email"],
                full_name=result.get("full_name"),
                username=result.get("username"),
                is_active=result["is_active"],
                is_verified=result["is_verified"],
                created_at=datetime.fromisoformat(result["created_at"]),
                updated_at=datetime.fromisoformat(result["updated_at"]),
                preferences=result.get("preferences", {}),
            )

        except Exception as e:
            logger.error(
                "Failed to create user",
                extra={"email": str(user_data.email), "error": str(e)},
            )
            raise

    async def get_user_by_id(self, user_id: str) -> UserResponse | None:
        """
        Retrieve user by ID.

        Args:
            user_id: User ID

        Returns:
            User information or None if not found
        """
        try:
            result = await self.db.get_user_by_id(user_id)
            if not result:
                return None

            return UserResponse(
                id=result["id"],
                email=result["email"],
                full_name=result.get("full_name"),
                username=result.get("username"),
                is_active=result["is_active"],
                is_verified=result["is_verified"],
                created_at=datetime.fromisoformat(result["created_at"]),
                updated_at=datetime.fromisoformat(result["updated_at"]),
                preferences=result.get("preferences", {}),
            )

        except Exception as e:
            logger.error(
                "Failed to get user by ID", extra={"user_id": user_id, "error": str(e)}
            )
            return None

    async def get_user_by_email(self, email: str) -> UserResponse | None:
        """
        Retrieve user by email address.

        Args:
            email: Email address

        Returns:
            User information or None if not found
        """
        try:
            result = await self.db.get_user_by_email(email)
            if not result:
                return None

            return UserResponse(
                id=result["id"],
                email=result["email"],
                full_name=result.get("full_name"),
                username=result.get("username"),
                is_active=result["is_active"],
                is_verified=result["is_verified"],
                created_at=datetime.fromisoformat(result["created_at"]),
                updated_at=datetime.fromisoformat(result["updated_at"]),
                preferences=result.get("preferences", {}),
            )

        except Exception as e:
            logger.error(
                "Failed to get user by email", extra={"email": email, "error": str(e)}
            )
            return None

    async def get_user_by_username(self, username: str) -> UserResponse | None:
        """
        Retrieve user by username.

        Args:
            username: Username

        Returns:
            User information or None if not found
        """
        try:
            result = await self.db.get_user_by_username(username)
            if not result:
                return None

            return UserResponse(
                id=result["id"],
                email=result["email"],
                full_name=result.get("full_name"),
                username=result.get("username"),
                is_active=result["is_active"],
                is_verified=result["is_verified"],
                created_at=datetime.fromisoformat(result["created_at"]),
                updated_at=datetime.fromisoformat(result["updated_at"]),
                preferences=result.get("preferences", {}),
            )

        except Exception as e:
            logger.error(
                "Failed to get user by username",
                extra={"username": username, "error": str(e)},
            )
            return None

    async def update_user(
        self, user_id: str, update_data: UserUpdateRequest
    ) -> UserResponse:
        """
        Update user information.

        Args:
            user_id: User ID
            update_data: Update data

        Returns:
            Updated user information

        Raises:
            NotFoundError: If user not found
            ValidationError: If update data is invalid
        """
        try:
            # Verify user exists
            existing_user = await self.get_user_by_id(user_id)
            if not existing_user:
                raise NotFoundError(f"User {user_id} not found")

            # Check username uniqueness if being updated
            if update_data.username and update_data.username != existing_user.username:
                existing_username = await self.get_user_by_username(
                    update_data.username
                )
                if existing_username and existing_username.id != user_id:
                    raise ValidationError(
                        f"Username {update_data.username} already taken"
                    )

            # Prepare update data
            db_update_data = update_data.model_dump(exclude_unset=True)
            db_update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

            # Update in database
            result = await self.db.update_user(user_id, db_update_data)

            logger.info(
                "User updated successfully",
                extra={
                    "user_id": user_id,
                    "updated_fields": list(db_update_data.keys()),
                },
            )

            return UserResponse(
                id=result["id"],
                email=result["email"],
                full_name=result.get("full_name"),
                username=result.get("username"),
                is_active=result["is_active"],
                is_verified=result["is_verified"],
                created_at=datetime.fromisoformat(result["created_at"]),
                updated_at=datetime.fromisoformat(result["updated_at"]),
                preferences=result.get("preferences", {}),
            )

        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            logger.error(
                "Failed to update user", extra={"user_id": user_id, "error": str(e)}
            )
            raise

    async def change_password(
        self, user_id: str, password_data: PasswordChangeRequest
    ) -> bool:
        """
        Change user password.

        Args:
            user_id: User ID
            password_data: Password change data

        Returns:
            True if successful

        Raises:
            NotFoundError: If user not found
            AuthenticationError: If current password is incorrect
        """
        try:
            # Get user with password hash
            user_data = await self.db.get_user_with_password(user_id)
            if not user_data:
                raise NotFoundError(f"User {user_id} not found")

            # Verify current password
            if not self._verify_password(
                password_data.current_password, user_data["hashed_password"]
            ):
                raise AuthenticationError("Current password is incorrect")

            # Hash new password
            new_hashed_password = self._hash_password(password_data.new_password)

            # Update password in database
            success = await self.db.update_user_password(user_id, new_hashed_password)

            if success:
                logger.info("Password changed successfully", extra={"user_id": user_id})

            return success

        except (NotFoundError, AuthenticationError):
            raise
        except Exception as e:
            logger.error(
                "Failed to change password",
                extra={"user_id": user_id, "error": str(e)},
            )
            raise

    async def verify_user_credentials(
        self, identifier: str, password: str
    ) -> UserResponse | None:
        """
        Verify user credentials for authentication.

        Args:
            identifier: Email or username
            password: Password

        Returns:
            User information if credentials are valid, None otherwise
        """
        try:
            # Try to find user by email first, then username
            user_data = None
            if "@" in identifier:
                user_data = await self.db.get_user_with_password_by_email(identifier)
            else:
                user_data = await self.db.get_user_with_password_by_username(identifier)

            if not user_data:
                return None

            # Verify password
            if not self._verify_password(password, user_data["hashed_password"]):
                return None

            # Check if user is active
            if not user_data["is_active"]:
                return None

            # Return user response (excluding password)
            return UserResponse(
                id=user_data["id"],
                email=user_data["email"],
                full_name=user_data.get("full_name"),
                username=user_data.get("username"),
                is_active=user_data["is_active"],
                is_verified=user_data["is_verified"],
                created_at=datetime.fromisoformat(user_data["created_at"]),
                updated_at=datetime.fromisoformat(user_data["updated_at"]),
                preferences=user_data.get("preferences", {}),
            )

        except Exception as e:
            logger.error(
                "Failed to verify credentials",
                extra={"identifier": identifier, "error": str(e)},
            )
            return None

    async def deactivate_user(self, user_id: str) -> bool:
        """
        Deactivate user account.

        Args:
            user_id: User ID

        Returns:
            True if successful

        Raises:
            NotFoundError: If user not found
        """
        try:
            update_data = UserUpdateRequest(is_active=False)
            await self.update_user(user_id, update_data)

            logger.info("User deactivated", extra={"user_id": user_id})
            return True

        except NotFoundError:
            raise
        except Exception as e:
            logger.error(
                "Failed to deactivate user",
                extra={"user_id": user_id, "error": str(e)},
            )
            return False

    async def activate_user(self, user_id: str) -> bool:
        """
        Activate user account.

        Args:
            user_id: User ID

        Returns:
            True if successful

        Raises:
            NotFoundError: If user not found
        """
        try:
            update_data = UserUpdateRequest(is_active=True)
            await self.update_user(user_id, update_data)

            logger.info("User activated", extra={"user_id": user_id})
            return True

        except NotFoundError:
            raise
        except Exception as e:
            logger.error(
                "Failed to activate user", extra={"user_id": user_id, "error": str(e)}
            )
            return False

    async def update_user_preferences(
        self, user_id: str, preferences: dict[str, Any]
    ) -> UserResponse:
        """
        Update user preferences.

        Args:
            user_id: User ID
            preferences: New preferences to merge

        Returns:
            Updated user information

        Raises:
            NotFoundError: If user not found
        """
        try:
            # Get current user
            user_data = await self.db.get_user_by_id(user_id)
            if not user_data:
                raise NotFoundError(f"User {user_id} not found")

            # Merge preferences (deep merge)
            current_preferences = user_data.get("preferences", {})
            merged_preferences = self._merge_preferences(
                current_preferences, preferences
            )

            # Update in database
            updated_at = datetime.now(timezone.utc).isoformat()
            await self.db.update_user_preferences(
                user_id, merged_preferences, updated_at
            )

            # Return updated user
            return UserResponse(
                id=user_data["id"],
                email=user_data["email"],
                full_name=user_data.get("full_name"),
                username=user_data.get("username"),
                is_active=user_data["is_active"],
                is_verified=user_data["is_verified"],
                created_at=datetime.fromisoformat(user_data["created_at"]),
                updated_at=datetime.fromisoformat(updated_at),
                preferences=merged_preferences,
            )

        except NotFoundError:
            raise
        except Exception as e:
            logger.error(
                "Failed to update user preferences",
                extra={"user_id": user_id, "error": str(e)},
            )
            raise

    def _merge_preferences(
        self, current: dict[str, Any], updates: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Deep merge preference dictionaries.

        Args:
            current: Current preferences
            updates: Updates to apply

        Returns:
            Merged preferences
        """
        result = current.copy()

        for key, value in updates.items():
            if (
                isinstance(value, dict)
                and key in result
                and isinstance(result[key], dict)
            ):
                # Recursively merge nested dictionaries
                result[key] = self._merge_preferences(result[key], value)
            else:
                # Override at current level
                result[key] = value

        return result

    def _hash_password(self, password: str) -> str:
        """
        Hash a password using bcrypt.

        Args:
            password: Plain password

        Returns:
            Hashed password
        """
        return self._pwd_context.hash(password)

    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash.

        Args:
            plain_password: Plain password
            hashed_password: Hashed password

        Returns:
            True if password matches
        """
        return self._pwd_context.verify(plain_password, hashed_password)

# Dependency function for FastAPI
async def get_user_service(database_service=None) -> UserService:
    """
    Get user service instance for dependency injection.

    Args:
        database_service: Database service instance

    Returns:
        UserService instance
    """
    return UserService(database_service=database_service)
