"""Pydantic schemas for BYOK API key management.

These models define request/response payloads for the API key endpoints.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


AllowedService = Literal["openai", "openrouter", "anthropic", "xai"]


class ApiKeyCreateRequest(BaseModel):
    """Request payload to add or replace a user's API key.

    Attributes:
        service: Provider identifier (one of allowed providers).
        api_key: Plaintext API key provided by the user.
    """

    service: AllowedService = Field(..., description="Target provider")
    api_key: str = Field(..., min_length=1, description="User-provided API key")


class ApiKeyResponse(BaseModel):
    """Summary of a stored API key (no secret material).

    Attributes:
        service: Provider identifier.
        created_at: Creation timestamp of metadata row.
        last_used: Optional timestamp of last successful use.
        has_key: Always true for listed entries.
        is_valid: Optimistic validity flag; actual validation occurs on use.
    """

    service: AllowedService
    created_at: datetime
    last_used: datetime | None = None
    has_key: bool = True
    is_valid: bool = True


class ApiKeyValidateRequest(BaseModel):
    """Request payload to validate a provider API key without storing it."""

    service: AllowedService = Field(..., description="Target provider")
    api_key: str = Field(..., min_length=1, description="API key to validate")


class ApiKeyValidateResponse(BaseModel):
    """Validation result for a provider API key."""

    is_valid: bool
    reason: str | None = None
