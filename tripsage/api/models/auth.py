"""Authentication models using Pydantic V2.

This module defines Pydantic models for authentication-related requests
and responses.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


class Token(BaseModel):
    """Token response model."""
    
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_at: datetime


class TokenData(BaseModel):
    """Token data model."""
    
    user_id: str
    scopes: List[str] = []
    exp: datetime


class UserCreate(BaseModel):
    """User creation request model."""
    
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    """User login request model."""
    
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """User response model."""
    
    id: str
    email: EmailStr
    full_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class RefreshToken(BaseModel):
    """Refresh token request model."""
    
    refresh_token: str