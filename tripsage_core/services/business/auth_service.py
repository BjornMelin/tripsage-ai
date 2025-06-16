"""
Optimized Supabase Authentication Service for FastAPI.

This implementation follows community best practices by:
1. Using local JWT validation for performance (avoids 600ms+ network calls)
2. Leveraging Supabase Python client for user management
3. Keeping the service lean and focused on authentication
4. Following the dependency injection pattern from the PRD

Based on research from:
- Supabase Python client documentation
- FastAPI + Supabase community examples
- Performance optimization recommendations
"""

from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from supabase import Client, create_client
from tripsage_core.config import get_settings
from tripsage_core.models.base_core_model import TripSageModel


class TokenData(TripSageModel):
    """Token data extracted from Supabase JWT tokens."""

    user_id: str
    email: Optional[str] = None
    role: Optional[str] = None
    aud: str = "authenticated"


# Security scheme for extracting Bearer tokens
security = HTTPBearer()


def get_supabase_client() -> Client:
    """
    Get Supabase client instance for user management operations.

    Returns:
        Supabase client configured with service key for admin operations
    """
    settings = get_settings()
    return create_client(
        settings.database.supabase_url,
        settings.database.supabase_service_role_key.get_secret_value(),
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> TokenData:
    """
    Validate Supabase JWT token and return user data.

    Uses local JWT validation for optimal performance (avoids 600ms+ network calls).
    This is the community-recommended approach for FastAPI + Supabase integration.

    Args:
        credentials: Bearer token from Authorization header

    Returns:
        TokenData with validated user information

    Raises:
        HTTPException: If token is invalid or expired
    """
    settings = get_settings()
    token = credentials.credentials

    try:
        # Local JWT validation - fast and efficient
        payload = jwt.decode(
            token,
            settings.database.supabase_jwt_secret.get_secret_value(),
            algorithms=["HS256"],
            audience="authenticated",
        )

        return TokenData(
            user_id=payload["sub"],
            email=payload.get("email"),
            role=payload.get("role", "authenticated"),
            aud=payload.get("aud", "authenticated"),
        )

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired"
        ) from None
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        ) from None
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token validation failed: {str(e)}",
        ) from e


async def get_user_with_client(
    token_data: TokenData = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
) -> dict:
    """
    Get full user details using Supabase client.

    Use this dependency when you need full user profile data.
    For most cases, get_current_user() is sufficient and faster.

    Args:
        token_data: Validated token data
        supabase: Supabase client for user operations

    Returns:
        Full user object from Supabase
    """
    try:
        user_response = supabase.auth.admin.get_user_by_id(token_data.user_id)
        if not user_response.user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )
        return user_response.user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch user details: {str(e)}",
        ) from e
