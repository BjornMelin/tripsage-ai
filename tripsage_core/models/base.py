"""
Base model classes for TripSage.

This module provides the base model classes used throughout the TripSage application,
establishing common behaviors and configurations.
"""

from pydantic import BaseModel, ConfigDict


class TripSageModel(BaseModel):
    """Base model for all TripSage models."""

    model_config = ConfigDict(
        populate_by_name=True,
        validate_assignment=True,
        extra="ignore",
    )


class TripSageBaseResponse(TripSageModel):
    """Base model for all TripSage API responses."""

    model_config = ConfigDict(
        populate_by_name=True,
        validate_assignment=True,
        extra="allow",
    )