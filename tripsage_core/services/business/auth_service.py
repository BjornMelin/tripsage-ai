"""Supabase Authentication Service for FastAPI.

Replaces local JWT decoding with Supabase's official Python SDK to validate
access tokens and resolve users. Keeps the service focused, leveraging
library-native behavior for correctness and maintainability.
"""

from __future__ import annotations

from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from tripsage_core.models.base_core_model import TripSageModel
from tripsage_core.services.infrastructure.supabase_client import (
    get_admin_client,
    verify_and_get_claims,
)


class TokenData(TripSageModel):
    """Token data extracted from Supabase user session."""

    user_id: str
    email: str | None = None
    role: str | None = None
    aud: str = "authenticated"


# Security scheme for extracting Bearer tokens
security = HTTPBearer()


async def _admin() -> Any:
    """Dependency wrapper to provide an async admin client."""
    return await get_admin_client()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> TokenData:
    """Validate token with Supabase and return token data.

    Args:
        credentials: Bearer token from Authorization header

    Returns:
        TokenData with user information

    Raises:
        HTTPException: If token is invalid or expired
    """
    token = credentials.credentials

    try:
        claims = await verify_and_get_claims(token)
        user_id = str(claims.get("sub"))
        email = claims.get("email")
        return TokenData(
            user_id=user_id,
            email=email,
            role=claims.get("role"),
            aud=claims.get("aud", "authenticated"),
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        ) from exc


async def get_user_with_client(
    token_data: TokenData = Depends(get_current_user),
    supabase: Any = Depends(_admin),
) -> dict[str, Any]:
    """Get full user details using Supabase admin client.

    Args:
        token_data: Validated token data
        supabase: Supabase client for user operations

    Returns:
        Full user object as a dict
    """
    try:
        resp = await supabase.auth.admin.get_user_by_id(token_data.user_id)
        if not getattr(resp, "user", None):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )
        # Convert user object to plain dict for downstream compatibility
        user_obj = resp.user
        return {
            "id": str(getattr(user_obj, "id", "")),
            "email": getattr(user_obj, "email", None),
            "user_metadata": getattr(user_obj, "user_metadata", {}) or {},
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch user details: {exc!s}",
        ) from exc
