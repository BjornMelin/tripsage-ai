"""Supabase-authenticated user extraction for TripSage API.

Uses Supabase's async SDK to validate tokens via JWKS (claims-first) and
return the current user's id. This avoids per-request calls to the Auth server
and eliminates blocking I/O in async code paths.
"""

from __future__ import annotations

import logging

from fastapi import Header, HTTPException, status

from tripsage_core.services.infrastructure.supabase_client import (
    verify_and_get_claims,
)


logger = logging.getLogger(__name__)


async def get_current_user_id(authorization: str | None = Header(None)) -> str:
    """Validate Authorization bearer token with Supabase and return user ID.

    Args:
        authorization: Authorization header with Bearer token.

    Returns:
        The authenticated user's UUID string.

    Raises:
        HTTPException: 401 if token is missing or invalid.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.replace("Bearer ", "", 1).strip()

    try:
        claims = await verify_and_get_claims(token)
        user_id = claims.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
            )
        return str(user_id)
    except HTTPException:
        raise
    except Exception as exc:  # Catch SDK/HTTP errors explicitly at boundary
        logger.warning("Supabase claim verification failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        ) from exc


async def get_optional_user_id(
    authorization: str | None = Header(None),
) -> str | None:
    """Get user ID if authenticated; return None otherwise.

    Args:
        authorization: Authorization header with Bearer token.

    Returns:
        Authenticated user UUID string, or None when unauthenticated/invalid.
    """
    if not authorization:
        return None
    try:
        return await get_current_user_id(authorization)
    except HTTPException:
        return None
