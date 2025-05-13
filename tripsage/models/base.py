"""
Base models for the TripSage application.
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class BaseResponseModel(BaseModel):
    """Base model for all API responses."""

    success: bool = Field(True, description="Whether the operation was successful")
    message: Optional[str] = Field(
        None, description="Message describing the operation result"
    )
    data: Optional[Any] = Field(None, description="Response data")


class ErrorResponseModel(BaseResponseModel):
    """Error response model."""

    success: bool = Field(False, description="Operation failed")
    error_code: Optional[str] = Field(None, description="Error code")
    error_details: Optional[Dict[str, Any]] = Field(
        None, description="Detailed error information"
    )
