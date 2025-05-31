"""Auth common models using Pydantic V2.

This module defines shared Pydantic models for authentication-related data structures.
"""

from typing import Optional

from pydantic import BaseModel, Field


class TokenData(BaseModel):
    """Model for token data."""

    username: Optional[str] = Field(default=None, description="Username")
    user_id: Optional[str] = Field(default=None, description="User ID")
    scopes: list[str] = Field(default=[], description="Token scopes")
    expires_at: Optional[int] = Field(default=None, description="Expiration timestamp")
