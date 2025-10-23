"""Base model classes for TripSage Core.

This module provides the centralized base model classes used throughout the entire
TripSage application, establishing common behaviors and configurations for both
domain models and database models.
"""

from pydantic import BaseModel, ConfigDict


class TripSageModel(BaseModel):
    """Base model for all TripSage models.

    This is the fundamental base class that all TripSage models should inherit from.
    It provides common configuration and validation behaviors that ensure consistency
    across the entire application.

    Features:
    - Pydantic v2 configuration
    - Populate by name (alias support)
    - Validate on assignment
    - Ignore extra fields
    """

    model_config = ConfigDict(
        populate_by_name=True,
        validate_assignment=True,
        extra="ignore",
    )


class TripSageBaseResponse(TripSageModel):
    """Base model for all TripSage API responses.

    This extends TripSageModel with specific configuration for API responses,
    allowing extra fields for forward compatibility and API evolution.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        validate_assignment=True,
        extra="allow",  # Allow extra fields for API compatibility
    )


class TripSageDomainModel(TripSageModel):
    """Base model for core business domain entities.

    This provides a specific base for domain models that represent core business
    entities like accommodations, flights, trips, etc. Domain models should be
    independent of storage implementation details.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        validate_assignment=True,
        extra="ignore",
        # Additional domain-specific configuration can be added here
    )


class TripSageDBModel(TripSageModel):
    """Base model for database-related models.

    This provides a specific base for models that interact with database storage,
    including both SQL and vector database models.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        validate_assignment=True,
        extra="ignore",
        from_attributes=True,  # Enable ORM mode for SQLAlchemy compatibility
    )
