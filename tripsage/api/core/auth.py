"""
Simple JWT authentication for TripSage API.

This module provides clean, maintainable authentication following FastAPI
best practices. Replaces complex middleware with simple dependency injection.
"""

import logging
from typing import Optional

import jwt
from fastapi import Header, HTTPException, status

from tripsage_core.config import get_settings

logger = logging.getLogger(__name__)

async def get_current_user_id(authorization: str | None = Header(None)) -> str:
    """
    Verify JWT token and return user ID.

    Simple, maintainable authentication dependency following FastAPI best practices.

    Args:
        authorization: Authorization header with Bearer token

    Returns:
        User ID string from JWT sub claim

    Raises:
        HTTPException: 401 if token is missing, invalid, or expired
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.replace("Bearer ", "")
    settings = get_settings()

    try:
        payload = jwt.decode(
            token,
            settings.database_jwt_secret.get_secret_value(),
            algorithms=["HS256"],
            audience="authenticated",
        )
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload"
            )
        return user_id
    except jwt.ExpiredSignatureError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired"
        ) from e
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        ) from e

async def get_optional_user_id(
    authorization: str | None = Header(None),
) -> str | None:
    """
    Get user ID if authenticated, None otherwise.

    For endpoints that work with or without authentication.

    Args:
        authorization: Authorization header with Bearer token

    Returns:
        User ID string if authenticated, None otherwise
    """
    if not authorization:
        return None
    try:
        return await get_current_user_id(authorization)
    except HTTPException:
        return None
