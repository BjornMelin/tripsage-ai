"""API key response models using Pydantic V2.

This module defines Pydantic models for API key-related responses.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ApiKeyResponse(BaseModel):
    """API key response model."""

    id: str
    name: str
    service: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime] = None
    is_valid: bool = True
    last_used: Optional[datetime] = None


class ApiKeyValidateResponse(BaseModel):
    """API key validation response model."""

    is_valid: bool
    service: str
    message: str
