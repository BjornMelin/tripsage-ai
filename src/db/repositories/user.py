"""
User repository for TripSage.

This module provides the User repository for interacting with the users table.
"""

from typing import Any, Dict, List, Optional

from src.db.models.user import User
from src.db.repositories.base import BaseRepository
from src.utils.logging import configure_logging

# Configure logging
logger = configure_logging(__name__)


class UserRepository(BaseRepository[User]):
    """
    Repository for User entities.

    This repository provides methods for interacting with the users table.
    """

    def __init__(self):
        """Initialize the repository with the User model class."""
        super().__init__(User)

    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Get a user by email address.

        Args:
            email: The email address to search for.

        Returns:
            The user if found, None otherwise.
        """
        # Email should be case-insensitive
        email = email.lower()
        return await self.find_one_by(email=email)

    async def find_by_name_pattern(self, name_pattern: str) -> List[User]:
        """
        Find users by name pattern.

        Args:
            name_pattern: The name pattern to search for (e.g., 'john%').

        Returns:
            List of users matching the pattern.
        """
        try:
            response = (
                self._get_table().select("*").ilike("name", name_pattern).execute()
            )
            if not response.data:
                return []

            return User.from_rows(response.data)
        except Exception as e:
            logger.error(f"Error finding users by name pattern: {e}")
            raise

    async def update_preferences(
        self, user_id: int, preferences: Dict[str, Any]
    ) -> Optional[User]:
        """
        Update a user's preferences.

        Args:
            user_id: The ID of the user to update.
            preferences: The new preferences to merge with existing ones.

        Returns:
            The updated user if found, None otherwise.
        """
        user = await self.get_by_id(user_id)
        if not user:
            return None

        # Get current preferences or initialize as empty dict
        current_prefs = user.preferences_json or {}

        # Deep merge preferences
        for key, value in preferences.items():
            if (
                isinstance(value, dict)
                and key in current_prefs
                and isinstance(current_prefs[key], dict)
            ):
                # Merge nested dictionaries
                current_prefs[key] = {**current_prefs[key], **value}
            else:
                # Override at top level
                current_prefs[key] = value

        # Update the user's preferences
        user.preferences_json = current_prefs

        # Save the updated user
        return await self.update(user)

    async def set_admin_status(self, user_id: int, is_admin: bool) -> Optional[User]:
        """
        Set a user's admin status.

        Args:
            user_id: The ID of the user to update.
            is_admin: Whether the user should be an admin.

        Returns:
            The updated user if found, None otherwise.
        """
        user = await self.get_by_id(user_id)
        if not user:
            return None

        user.is_admin = is_admin
        return await self.update(user)

    async def set_disabled_status(
        self, user_id: int, is_disabled: bool
    ) -> Optional[User]:
        """
        Set a user's disabled status.

        Args:
            user_id: The ID of the user to update.
            is_disabled: Whether the user should be disabled.

        Returns:
            The updated user if found, None otherwise.
        """
        user = await self.get_by_id(user_id)
        if not user:
            return None

        user.is_disabled = is_disabled
        return await self.update(user)

    async def update_password(self, user_id: int, password_hash: str) -> Optional[User]:
        """
        Update a user's password hash.

        Args:
            user_id: The ID of the user to update.
            password_hash: The new password hash.

        Returns:
            The updated user if found, None otherwise.
        """
        user = await self.get_by_id(user_id)
        if not user:
            return None

        user.password_hash = password_hash
        return await self.update(user)

    async def get_admins(self) -> List[User]:
        """
        Get all admin users.

        Returns:
            List of admin users.
        """
        return await self.find_by(is_admin=True)
