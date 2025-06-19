"""API Key API schemas using Pydantic V2.

This module defines Pydantic models for API key-related API requests and responses.
Consolidates both request and response schemas for API key operations.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

# ===== Request Schemas =====


class ApiKeyCreate(BaseModel):
    """API key creation request model."""

    name: str = Field(min_length=1, max_length=255)
    service: str = Field(min_length=1, max_length=255)
    key: str
    description: Optional[str] = None
    expires_at: Optional[datetime] = None


class ApiKeyValidateRequest(BaseModel):
    """API key validation request model."""

    key: str
    service: str


class ApiKeyRotateRequest(BaseModel):
    """API key rotation request model."""

    new_key: str


# ===== Response Schemas =====


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


class ApiKeyListResponse(BaseModel):
    """API key list response model."""

    api_keys: List[ApiKeyResponse] = Field(description="List of API keys")
    count: int = Field(description="Number of API keys")
