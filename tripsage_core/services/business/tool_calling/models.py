"""Tool calling service models."""

from __future__ import annotations

import time
from typing import Any

from pydantic import BaseModel, Field, field_validator

from tripsage_core.exceptions.exceptions import CoreTripSageError as TripSageError


class ToolCallError(TripSageError):
    """Error raised when tool calling fails."""


class ToolCallRequest(BaseModel):
    """Structured tool call request model."""

    id: str = Field(..., description="Unique identifier for the tool call")
    service: str = Field(..., description="MCP service name")
    method: str = Field(..., description="Method to invoke")
    params: dict[str, Any] = Field(
        default_factory=dict, description="Method parameters"
    )
    timeout: float | None = Field(default=30.0, description="Timeout in seconds")
    retry_count: int = Field(default=3, description="Number of retries on failure")

    @field_validator("service")
    @classmethod
    def validate_service(cls, v: str) -> str:
        """Validate service name."""
        allowed_services = [
            "duffel_flights",
            "airbnb",
            "google_maps",
            "supabase",
            "memory",
            "time",
            "firecrawl",
            "linkup",
        ]
        if v not in allowed_services:
            raise ValueError(
                f"Service '{v}' not in allowed services: {allowed_services}"
            )
        return v

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: float | None) -> float | None:
        """Validate timeout value."""
        if v is not None and (v <= 0 or v > 300):
            raise ValueError("Timeout must be between 0 and 300 seconds")
        return v


class ToolCallResponse(BaseModel):
    """Structured tool call response model."""

    id: str = Field(..., description="Tool call identifier")
    status: str = Field(..., description="Response status (success/error/timeout)")
    result: dict[str, Any] | None = Field(default=None, description="Tool result data")
    error: str | None = Field(default=None, description="Error message if failed")
    execution_time: float = Field(..., description="Execution time in seconds")
    service: str = Field(..., description="MCP service used")
    method: str = Field(..., description="Method invoked")
    timestamp: float = Field(
        default_factory=time.time, description="Response timestamp"
    )


class ToolCallValidationResult(BaseModel):
    """Tool call validation result."""

    is_valid: bool = Field(..., description="Whether tool call is valid")
    errors: list[str] = Field(default_factory=list, description="Validation errors")
    sanitized_params: dict[str, Any] | None = Field(
        default=None, description="Sanitized parameters"
    )
