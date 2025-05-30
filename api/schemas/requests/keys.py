"""
Request schemas for API key management endpoints.

This module defines Pydantic models for validating incoming API key management
requests from the Next.js frontend.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class CreateApiKeyRequest(BaseModel):
    """Request schema for creating an API key."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Descriptive name for the API key",
    )
    service: str = Field(
        ...,
        description="Service name (openai, weather, flights, etc.)",
    )
    key_value: str = Field(
        ...,
        min_length=1,
        description="The actual API key value",
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="Optional description of the key",
    )
    expires_at: Optional[datetime] = Field(
        None,
        description="Optional expiration date for the key",
    )

    @field_validator("service")
    @classmethod
    def validate_service(cls, v: str) -> str:
        """Validate service name."""
        allowed_services = {
            "openai",
            "weather",
            "flights",
            "googlemaps",
            "accommodation",
            "webcrawl",
            "calendar",
            "email",
        }
        if v.lower() not in allowed_services:
            raise ValueError(f"Service must be one of: {', '.join(allowed_services)}")
        return v.lower()


class UpdateApiKeyRequest(BaseModel):
    """Request schema for updating an API key."""

    name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        description="New name for the API key",
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="New description for the key",
    )
    expires_at: Optional[datetime] = Field(
        None,
        description="New expiration date for the key",
    )


class RotateApiKeyRequest(BaseModel):
    """Request schema for rotating an API key."""

    new_key_value: str = Field(
        ...,
        min_length=1,
        description="The new API key value",
    )


class ValidateApiKeyRequest(BaseModel):
    """Request schema for validating an API key."""

    service: str = Field(
        ...,
        description="Service name to validate against",
    )
    key_value: str = Field(
        ...,
        min_length=1,
        description="The API key value to validate",
    )

    @field_validator("service")
    @classmethod
    def validate_service(cls, v: str) -> str:
        """Validate service name."""
        allowed_services = {
            "openai",
            "weather",
            "flights",
            "googlemaps",
            "accommodation",
            "webcrawl",
            "calendar",
            "email",
        }
        if v.lower() not in allowed_services:
            raise ValueError(f"Service must be one of: {', '.join(allowed_services)}")
        return v.lower()
