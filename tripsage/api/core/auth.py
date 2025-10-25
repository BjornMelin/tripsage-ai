"""Supabase-authenticated user extraction for TripSage API.

This module replaces local JWT decoding with Supabase's official Python SDK
for token validation and user resolution. It provides clean, maintainable
FastAPI dependencies aligned with library-native behavior (KISS/DRY).
"""

from __future__ import annotations

import logging

from fastapi import Header, HTTPException, status
from supabase import Client, create_client

from tripsage_core.config import get_settings


logger = logging.getLogger(__name__)


def _supabase_client() -> Client:
    """Create a Supabase client using service role credentials.

    Returns:
        Client: Supabase admin client for server-side auth operations.
    """
    settings = get_settings()
    return create_client(
        # pylint: disable=no-member # type: ignore
        settings.database_url,
        settings.database_service_key.get_secret_value(),
    )


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
        supabase = _supabase_client()
        user_resp = supabase.auth.get_user(token)
        user = getattr(user_resp, "user", None)
        if not user or not getattr(user, "id", None):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
            )
        return str(user.id)
    except HTTPException:
        raise
    except Exception as exc:  # Catch SDK/HTTP errors explicitly at boundary
        logger.warning("Supabase auth validation failed: %s", exc)
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
