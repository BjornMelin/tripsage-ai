"""
Response schemas for API key management endpoints.

This module defines Pydantic models for API responses related to API key management
from the backend to the Next.js frontend.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ApiKeyResponse(BaseModel):
    """Response schema for API key information."""

    id: str = Field(..., description="API key ID")
    name: str = Field(..., description="API key name")
    service: str = Field(..., description="Service name")
    description: Optional[str] = Field(None, description="API key description")
    is_valid: bool = Field(..., description="Whether the key is valid")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")
    last_used: Optional[datetime] = Field(None, description="Last usage timestamp")
    last_validated: Optional[datetime] = Field(
        None, description="Last validation timestamp"
    )
    usage_count: int = Field(default=0, description="Number of times used")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "key_123",
                "name": "My OpenAI Key",
                "service": "openai",
                "description": "API key for OpenAI GPT models",
                "is_valid": True,
                "created_at": "2025-01-15T14:30:00Z",
                "updated_at": "2025-01-16T09:45:00Z",
                "expires_at": None,
                "last_used": "2025-01-16T09:45:00Z",
                "last_validated": "2025-01-15T14:30:00Z",
                "usage_count": 42,
            }
        }
    }


class ApiKeyListResponse(BaseModel):
    """Response schema for list of API keys."""

    keys: List[ApiKeyResponse] = Field(..., description="List of API keys")
    total: int = Field(..., description="Total number of keys")

    model_config = {
        "json_schema_extra": {
            "example": {
                "keys": [
                    {
                        "id": "key_123",
                        "name": "My OpenAI Key",
                        "service": "openai",
                        "description": "API key for OpenAI GPT models",
                        "is_valid": True,
                        "created_at": "2025-01-15T14:30:00Z",
                        "updated_at": "2025-01-16T09:45:00Z",
                        "expires_at": None,
                        "last_used": "2025-01-16T09:45:00Z",
                        "last_validated": "2025-01-15T14:30:00Z",
                        "usage_count": 42,
                    }
                ],
                "total": 1,
            }
        }
    }


class ApiKeyValidationResponse(BaseModel):
    """Response schema for API key validation."""

    is_valid: bool = Field(..., description="Whether the key is valid")
    service: str = Field(..., description="Service name")
    message: str = Field(..., description="Validation message")
    details: Optional[Dict[str, Any]] = Field(
        None, description="Additional validation details"
    )
    validated_at: datetime = Field(..., description="Validation timestamp")

    model_config = {
        "json_schema_extra": {
            "example": {
                "is_valid": True,
                "service": "openai",
                "message": "API key is valid and active",
                "details": {
                    "validation_type": "api_call",
                    "response_time_ms": 245,
                },
                "validated_at": "2025-01-16T09:45:00Z",
            }
        }
    }


class ApiKeyServiceStatusResponse(BaseModel):
    """Response schema for API key service status."""

    service: str = Field(..., description="Service name")
    has_key: bool = Field(..., description="Whether user has a key for this service")
    is_valid: Optional[bool] = Field(None, description="Whether the key is valid")
    last_validated: Optional[datetime] = Field(
        None, description="Last validation timestamp"
    )
    last_used: Optional[datetime] = Field(None, description="Last usage timestamp")

    model_config = {
        "json_schema_extra": {
            "example": {
                "service": "openai",
                "has_key": True,
                "is_valid": True,
                "last_validated": "2025-01-15T14:30:00Z",
                "last_used": "2025-01-16T09:45:00Z",
            }
        }
    }


class ApiKeyServicesStatusResponse(BaseModel):
    """Response schema for all services API key status."""

    services: Dict[str, ApiKeyServiceStatusResponse] = Field(
        ..., description="Status for each service"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "services": {
                    "openai": {
                        "service": "openai",
                        "has_key": True,
                        "is_valid": True,
                        "last_validated": "2025-01-15T14:30:00Z",
                        "last_used": "2025-01-16T09:45:00Z",
                    },
                    "weather": {
                        "service": "weather",
                        "has_key": False,
                        "is_valid": None,
                        "last_validated": None,
                        "last_used": None,
                    },
                }
            }
        }
    }


class MessageResponse(BaseModel):
    """Response schema for simple messages."""

    message: str = Field(..., description="Message")
    success: bool = Field(True, description="Whether the operation was successful")

    model_config = {
        "json_schema_extra": {
            "example": {"message": "Operation completed successfully", "success": True}
        }
    }
