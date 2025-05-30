"""
Authentication service for the TripSage API.

This service handles user registration, authentication, and token management.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import jwt
from passlib.context import CryptContext
from supabase import Client, create_client

from tripsage_core.config.base_app_settings import settings
from tripsage_core.exceptions.exceptions import (
    CoreAuthenticationError as AuthenticationError,
)

logger = logging.getLogger(__name__)


class AuthService:
    """Service for authentication and user management."""

    def __init__(self):
        """Initialize the authentication service."""
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.supabase: Optional[Client] = None

    async def _get_supabase_client(self) -> Client:
        """Get or create Supabase client."""
        if self.supabase is None:
            self.supabase = create_client(
                settings.supabase_url, settings.supabase_anon_key
            )
        return self.supabase

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against a hash.

        Args:
            plain_password: Plain password
            hashed_password: Hashed password

        Returns:
            True if the password matches the hash, False otherwise
        """
        return self.pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """Hash a password.

        Args:
            password: Plain password

        Returns:
            Hashed password
        """
        return self.pwd_context.hash(password)

    async def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get a user by username.

        Args:
            username: Username

        Returns:
            User information or None if not found
        """
        supabase = await self._get_supabase_client()
        return (
            await supabase.table("users").select("*").eq("username", username).execute()
        )

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get a user by email.

        Args:
            email: Email address

        Returns:
            User information or None if not found
        """
        supabase = await self._get_supabase_client()
        return await supabase.table("users").select("*").eq("email", email).execute()

    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get a user by ID.

        Args:
            user_id: User ID

        Returns:
            User information or None if not found
        """
        supabase = await self._get_supabase_client()
        return await supabase.table("users").select("*").eq("id", user_id).execute()

    async def authenticate_user(self, username: str, password: str) -> Dict[str, Any]:
        """Authenticate a user.

        Args:
            username: Username or email
            password: Password

        Returns:
            User information if authentication is successful

        Raises:
            AuthenticationError: If authentication fails
        """
        # Check if username is an email
        if "@" in username:
            user = await self.get_user_by_email(username)
        else:
            user = await self.get_user_by_username(username)

        if not user:
            raise AuthenticationError("Invalid username or password")

        if not self.verify_password(password, user["password"]):
            raise AuthenticationError("Invalid username or password")

        if not user["is_active"]:
            raise AuthenticationError("User is inactive")

        # Remove password from user info
        user_info = {k: v for k, v in user.items() if k != "password"}

        return user_info

    async def create_user(
        self,
        username: str,
        email: str,
        password: str,
        full_name: str,
    ) -> Dict[str, Any]:
        """Create a new user.

        Args:
            username: Username
            email: Email address
            password: Password
            full_name: Full name

        Returns:
            Created user information
        """
        # Hash the password
        hashed_password = self.get_password_hash(password)

        # Create user data
        user_data = {
            "username": username,
            "email": email,
            "password": hashed_password,
            "full_name": full_name,
            "is_active": True,
            "is_verified": False,
            "created_at": datetime.now(datetime.UTC).isoformat(),
            "updated_at": datetime.now(datetime.UTC).isoformat(),
            "preferences": {},
        }

        # Save the user
        supabase = await self._get_supabase_client()
        user = await supabase.table("users").insert(user_data).execute()

        # Remove password from user info
        user_info = {k: v for k, v in user.items() if k != "password"}

        return user_info

    async def create_access_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """Create a JWT access token.

        Args:
            data: Token payload
            expires_delta: Token expiration time

        Returns:
            JWT token
        """
        to_encode = data.copy()

        # Set expiration time
        if expires_delta:
            expire = datetime.now(datetime.UTC) + expires_delta
        else:
            expire = datetime.now(datetime.UTC) + timedelta(minutes=15)

        to_encode.update({"exp": expire, "type": "access"})

        # Encode the token
        encoded_jwt = jwt.encode(
            to_encode,
            settings.secret_key.get_secret_value(),
            algorithm=settings.algorithm,
        )

        return encoded_jwt

    async def create_refresh_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """Create a JWT refresh token.

        Args:
            data: Token payload
            expires_delta: Token expiration time

        Returns:
            JWT token
        """
        to_encode = data.copy()

        # Set expiration time
        if expires_delta:
            expire = datetime.now(datetime.UTC) + expires_delta
        else:
            expire = datetime.now(datetime.UTC) + timedelta(days=7)

        to_encode.update({"exp": expire, "type": "refresh"})

        # Encode the token
        encoded_jwt = jwt.encode(
            to_encode,
            settings.secret_key.get_secret_value(),
            algorithm=settings.algorithm,
        )

        return encoded_jwt

    async def validate_access_token(self, token: str) -> Dict[str, Any]:
        """Validate a JWT access token.

        Args:
            token: JWT token

        Returns:
            Token payload

        Raises:
            AuthenticationError: If token is invalid
        """
        try:
            # Decode the token
            payload = jwt.decode(
                token,
                settings.secret_key.get_secret_value(),
                algorithms=[settings.algorithm],
            )

            # Check token type
            if payload.get("type") != "access":
                raise AuthenticationError("Invalid token type")

            return payload

        except jwt.ExpiredSignatureError as e:
            raise AuthenticationError("Token has expired") from e
        except jwt.InvalidTokenError as e:
            raise AuthenticationError("Invalid token") from e

    async def validate_refresh_token(self, token: str) -> Dict[str, Any]:
        """Validate a JWT refresh token.

        Args:
            token: JWT token

        Returns:
            Token payload

        Raises:
            AuthenticationError: If token is invalid
        """
        try:
            # Decode the token
            payload = jwt.decode(
                token,
                settings.secret_key.get_secret_value(),
                algorithms=[settings.algorithm],
            )

            # Check token type
            if payload.get("type") != "refresh":
                raise AuthenticationError("Invalid token type")

            return payload

        except jwt.ExpiredSignatureError as e:
            raise AuthenticationError("Token has expired") from e
        except jwt.InvalidTokenError as e:
            raise AuthenticationError("Invalid token") from e

    async def create_password_reset_token(self, user_id: str) -> str:
        """Create a password reset token.

        Args:
            user_id: User ID

        Returns:
            Password reset token
        """
        to_encode = {
            "user_id": user_id,
            "type": "password_reset",
            "exp": datetime.now(datetime.UTC) + timedelta(hours=1),
        }

        # Encode the token
        encoded_jwt = jwt.encode(
            to_encode,
            settings.secret_key.get_secret_value(),
            algorithm=settings.algorithm,
        )

        return encoded_jwt

    async def change_password(
        self,
        user_id: str,
        current_password: str,
        new_password: str,
    ) -> bool:
        """Change a user's password.

        Args:
            user_id: User ID
            current_password: Current password
            new_password: New password

        Returns:
            True if successful, False otherwise

        Raises:
            AuthenticationError: If current password is incorrect
        """
        # Get the user
        user = await self.get_user_by_id(user_id)
        if not user:
            raise AuthenticationError("User not found")

        # Verify current password
        if not self.verify_password(current_password, user["password"]):
            raise AuthenticationError("Current password is incorrect")

        # Hash the new password
        hashed_password = self.get_password_hash(new_password)

        # Update the user
        supabase = await self._get_supabase_client()
        result = (
            await supabase.table("users")
            .update({"password": hashed_password})
            .eq("id", user_id)
            .execute()
        )

        return result is not None

    async def reset_password(self, token: str, new_password: str) -> bool:
        """Reset a user's password.

        Args:
            token: Reset token
            new_password: New password

        Returns:
            True if successful, False otherwise

        Raises:
            AuthenticationError: If the token is invalid
        """
        try:
            # Decode the token
            payload = jwt.decode(
                token,
                settings.secret_key.get_secret_value(),
                algorithms=[settings.algorithm],
            )

            # Check token type
            if payload.get("type") != "reset":
                raise AuthenticationError("Invalid token type")

            # Get the user
            user_id = payload.get("sub")
            user = await self.get_user_by_id(user_id)
            if not user:
                raise AuthenticationError("User not found")

            # Hash the new password
            hashed_password = self.get_password_hash(new_password)

            # Update the user
            supabase = await self._get_supabase_client()
            result = (
                await supabase.table("users")
                .update({"password": hashed_password})
                .eq("id", user_id)
                .execute()
            )

            return result is not None

        except jwt.ExpiredSignatureError as e:
            raise AuthenticationError("Token has expired") from e
        except jwt.InvalidTokenError as e:
            raise AuthenticationError("Invalid token") from e
