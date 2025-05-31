"""
Dependency injection for TripSage API.

This module centralizes all FastAPI dependencies for the TripSage API,
focusing on core services and JWT-based authentication.
"""

from typing import Optional, Union

from fastapi import Depends, Request, Security
from fastapi.security import APIKeyHeader, APIKeyQuery, OAuth2PasswordBearer

from tripsage.api.core.config import get_settings
from tripsage_core.exceptions.exceptions import (
    CoreAuthenticationError as AuthenticationError,
)
from tripsage_core.models.db.user import User
from tripsage_core.services.business.auth_service import (
    AuthenticationService as CoreAuthService,
)
from tripsage_core.services.business.auth_service import (
    get_auth_service as get_core_auth_service,
)
from tripsage_core.services.infrastructure import get_cache_service
from tripsage_core.utils.session_utils import SessionMemory

# Initialize settings after imports
settings = get_settings()

# OAuth2 setup
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/token", auto_error=False)

# API key authentication setup
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
api_key_query = APIKeyQuery(name="api_key", auto_error=False)


class ApiUser:
    """Simplified user class for API key authentication."""

    def __init__(self, api_key: str):
        self.id = "api_user"
        self.username = "api_user"
        self.email = None
        self.is_api = True
        self.is_active = True
        self.is_verified = True
        self.api_key = api_key


# Core auth service dependency
async def get_core_auth_service_dep() -> CoreAuthService:
    """Get the core auth service instance as a dependency.

    Returns:
        CoreAuthService instance
    """
    return await get_core_auth_service()


# Settings dependency
def get_settings_dependency():
    """Get settings instance as a dependency.

    Returns:
        Settings instance
    """
    return get_settings()


# Database dependency
async def get_db():
    """Get database session as a dependency.

    This is a placeholder function. In a full implementation,
    this would return an actual database session.
    """
    # Placeholder - implement when database integration is complete
    return None


# Session memory dependency
async def get_session_memory(request: Request) -> SessionMemory:
    """Get the session memory for the current request.

    Args:
        request: The current FastAPI request

    Returns:
        SessionMemory instance for the current session
    """
    if not hasattr(request.state, "session_memory"):
        # Create or get a session memory instance for this request
        session_id = request.cookies.get("session_id", None)

        if not session_id:
            # Generate a new session ID if it doesn't exist
            from uuid import uuid4

            session_id = str(uuid4())

        # Initialize session memory
        request.state.session_memory = SessionMemory(session_id=session_id)

    return request.state.session_memory


# Authentication dependencies
_core_auth_service_dep = Depends(get_core_auth_service_dep)


async def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme),
    api_key_header: Optional[str] = Security(api_key_header),
    api_key_query: Optional[str] = Security(api_key_query),
    auth_service: CoreAuthService = _core_auth_service_dep,
) -> Optional[Union[User, ApiUser]]:
    """Get the current user if authenticated, otherwise return None.

    Args:
        token: OAuth2 token
        api_key_header: API key from header
        api_key_query: API key from query parameter
        auth_service: Core authentication service

    Returns:
        User object if authenticated, None otherwise
    """
    # First check API key (from header or query)
    api_key = api_key_header or api_key_query

    if api_key:
        # Validate API key
        # This is a simplified implementation - in a real system,
        # you'd verify the key against a database
        if api_key.startswith("tripsage_"):
            # Return API user instance
            return ApiUser(api_key)

    # If no API key, check OAuth2 token
    if token:
        try:
            # Use core auth service for JWT validation
            user = await auth_service.get_current_user(token)
            return user
        except Exception:
            # Invalid token - return None for optional auth
            return None

    # No authentication provided
    return None


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    api_key_header: Optional[str] = Security(api_key_header),
    api_key_query: Optional[str] = Security(api_key_query),
    auth_service: CoreAuthService = _core_auth_service_dep,
) -> Union[User, ApiUser]:
    """Get the current authenticated user or raise an error.

    Args:
        token: OAuth2 token
        api_key_header: API key from header
        api_key_query: API key from query parameter
        auth_service: Core authentication service

    Returns:
        User object if authenticated

    Raises:
        AuthenticationError: If no user is authenticated
    """
    user = await get_current_user_optional(
        token, api_key_header, api_key_query, auth_service
    )
    if user is None:
        raise AuthenticationError("Not authenticated")
    return user


# Module-level dependency singletons to avoid B008 linting errors
get_current_user_dep = Depends(get_current_user)
get_current_user_optional_dep = Depends(get_current_user_optional)
get_db_dep = Depends(get_db)
get_session_memory_dep = Depends(get_session_memory)


async def verify_api_key(
    current_user: Union[User, ApiUser] = get_current_user_dep,
) -> bool:
    """Verify that the user has a valid API key for chat functionality.

    For now, this is a simplified check. In a full implementation,
    this would validate specific service keys (like OpenAI) from the database.

    Args:
        current_user: Current authenticated user

    Returns:
        True if user has valid API keys

    Raises:
        AuthenticationError: If no valid API key is found
    """
    # In a real implementation, you would:
    # 1. Query the database for the user's API keys
    # 2. Validate the keys against the respective services
    # 3. Return the validation status

    # For now, we'll assume authenticated users have valid keys
    # This will be enhanced when the full BYOK system is integrated
    return True


# Module-level dependency for API key verification
verify_api_key_dep = Depends(verify_api_key)


# Cache service dependency
async def get_cache_service_dep():
    """Get the cache service instance as a dependency."""
    return await get_cache_service()


# Define singleton dependencies
cache_service_dependency = Depends(get_cache_service_dep)
