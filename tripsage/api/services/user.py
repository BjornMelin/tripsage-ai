"""User service for TripSage API.

This module provides services for user management, including user creation,
retrieval, and updates.
"""

import logging
import uuid
from datetime import datetime
from typing import Optional

from passlib.context import CryptContext
from pydantic import EmailStr

from tripsage.api.models.auth import UserResponse
from tripsage.mcp_abstraction import get_mcp_manager

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserService:
    """User service for the TripSage API.
    
    This service handles user management, including user creation,
    retrieval, and updates.
    """
    
    def __init__(self):
        """Initialize the user service."""
        self.mcp_manager = get_mcp_manager()
    
    async def get_user_by_id(self, user_id: str) -> Optional[UserResponse]:
        """Get a user by ID.
        
        Args:
            user_id: The user ID
            
        Returns:
            The user if found, None otherwise
        """
        try:
            # Use Supabase MCP to get the user
            supabase_mcp = await self.mcp_manager.initialize_mcp("supabase")
            
            result = await supabase_mcp.invoke_method(
                "query",
                params={
                    "table": "users",
                    "query": {"id": user_id, "select": "*"},
                },
            )
            
            if not result or not result.get("data") or len(result["data"]) == 0:
                return None
            
            user_data = result["data"][0]
            
            # Create UserResponse model
            return UserResponse(
                id=user_data["id"],
                email=user_data["email"],
                full_name=user_data.get("full_name"),
                created_at=user_data["created_at"],
                updated_at=user_data["updated_at"],
            )
        except Exception as e:
            logger.error(f"Error getting user by ID: {e}")
            return None
    
    async def get_user_by_email(self, email: str) -> Optional[dict]:
        """Get a user by email.
        
        Args:
            email: The user email
            
        Returns:
            The user if found, None otherwise
        """
        try:
            # Use Supabase MCP to get the user
            supabase_mcp = await self.mcp_manager.initialize_mcp("supabase")
            
            result = await supabase_mcp.invoke_method(
                "query",
                params={
                    "table": "users",
                    "query": {"email": email, "select": "*"},
                },
            )
            
            if not result or not result.get("data") or len(result["data"]) == 0:
                return None
            
            return result["data"][0]
        except Exception as e:
            logger.error(f"Error getting user by email: {e}")
            return None
    
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
            Exception: If the user cannot be created
        """
        try:
            # Generate a user ID
            user_id = str(uuid.uuid4())
            
            # Hash the password
            hashed_password = pwd_context.hash(password)
            
            # Current time
            now = datetime.utcnow()
            
            # Use Supabase MCP to create the user
            supabase_mcp = await self.mcp_manager.initialize_mcp("supabase")
            
            result = await supabase_mcp.invoke_method(
                "insert",
                params={
                    "table": "users",
                    "data": {
                        "id": user_id,
                        "email": email,
                        "hashed_password": hashed_password,
                        "full_name": full_name,
                        "created_at": now.isoformat(),
                        "updated_at": now.isoformat(),
                    },
                },
            )
            
            if not result or not result.get("data") or len(result["data"]) == 0:
                raise Exception("Failed to create user")
            
            user_data = result["data"][0]
            
            # Create UserResponse model
            return UserResponse(
                id=user_data["id"],
                email=user_data["email"],
                full_name=user_data.get("full_name"),
                created_at=user_data["created_at"],
                updated_at=user_data["updated_at"],
            )
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            raise