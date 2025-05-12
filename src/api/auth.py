"""
Authentication module for the TripSage API.

This module provides JWT-based authentication for the TripSage API.
"""

import os
from datetime import datetime, timedelta
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from src.api.database import get_repository, get_user_repository
from src.db.repositories.user import UserRepository

# Load environment variables
load_dotenv()

# Auth constants
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "REPLACE_WITH_STRONG_SECRET_IN_PRODUCTION")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


# Create a user repository dependency
def get_user_repo_dependency():
    """Get the user repository dependency."""
    return get_repository(get_user_repository)


# Token models
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    user_id: Optional[str] = None


# User model
class User(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    disabled: Optional[bool] = None


# Create access token
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Create a JWT access token with the given data and expiration.

    Args:
        data: The data to encode in the token, should include 'sub' with user ID
        expires_delta: Optional timedelta for token expiration. Defaults to 30 minutes.

    Returns:
        The encoded JWT access token.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# Get current user
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    user_repo: UserRepository = None,
):
    """
    Get the current user from the JWT token.

    Args:
        token: The JWT token
        user_repo: The user repository

    Returns:
        The current user

    Raises:
        HTTPException: If the token is invalid or the user is not found
    """
    if user_repo is None:
        user_repo = get_user_repo_dependency()()

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Decode JWT token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        token_data = TokenData(user_id=user_id)
    except JWTError:
        raise credentials_exception from None

    # Get user from database
    user = await user_repo.get_by_id(int(token_data.user_id))
    if not user:
        raise credentials_exception

    # Convert to API user model
    api_user = User(
        id=str(user.id),
        email=user.email,
        full_name=user.name,
        disabled=user.is_disabled if hasattr(user, "is_disabled") else False,
    )

    return api_user


# Get active user
async def get_current_active_user(
    current_user: User = None,
):
    """
    Get the current active user.

    Args:
        current_user: The current user

    Returns:
        The current active user

    Raises:
        HTTPException: If the user is disabled
    """
    if current_user is None:
        current_user = await get_current_user()

    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user
