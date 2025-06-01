"""API key request models using Pydantic V2.

This module defines Pydantic models for API key-related requests.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


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
