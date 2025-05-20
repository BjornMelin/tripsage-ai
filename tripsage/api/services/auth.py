"""Authentication service for TripSage API.

This module provides services for authentication, including user authentication,
password validation, and token management.
"""

import logging
from datetime import datetime
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from tripsage.api.core.config import get_settings
from tripsage.api.services.user import UserService

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Authentication service for the TripSage API.

    This service handles user authentication, password validation,
    and token management.
    """

    def __init__(self, user_service: Optional[UserService] = None):
        """Initialize the authentication service.

        Args:
            user_service: User service for database operations
        """
        self.user_service = user_service or UserService()
        self.settings = get_settings()

    async def authenticate_user(self, email: str, password: str):
        """Authenticate a user with email and password.

        Args:
            email: User email
            password: User password

        Returns:
            The user if authentication is successful, None otherwise
        """
        user = await self.user_service.get_user_by_email(email)

        if not user:
            return None

        if not self.verify_password(password, user.hashed_password):
            return None

        return user

    async def validate_refresh_token(self, token: str):
        """Validate a refresh token.

        Args:
            token: The refresh token to validate

        Returns:
            The user if the token is valid, None otherwise
        """
        try:
            payload = jwt.decode(
                token,
                self.settings.secret_key,
                algorithms=["HS256"],
            )

            # Check if it's a refresh token
            if not payload.get("refresh"):
                return None

            # Check if token is expired
            if "exp" in payload and datetime.utcnow().timestamp() > payload["exp"]:
                return None

            # Get the user ID
            user_id = payload.get("user_id")
            if not user_id:
                return None

            # Get the user
            user = await self.user_service.get_user_by_id(user_id)
            if not user:
                return None

            return user
        except JWTError:
            return None

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against a hash.

        Args:
            plain_password: The plain password
            hashed_password: The hashed password

        Returns:
            True if the password is correct, False otherwise
        """
        return pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """Generate a password hash.

        Args:
            password: The password to hash

        Returns:
            The hashed password
        """
        return pwd_context.hash(password)
