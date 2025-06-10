"""
TripSage Core Package.

This package contains the centralized core functionality for the TripSage application,
including models, exceptions, and shared utilities.

Modules:
- models: Core data models and schemas
- exceptions: Centralized exception handling system
- config: Core configuration settings
- utilities: Shared utility functions and helpers

Usage:
    # Import core models
    from tripsage_core.models import TripSageModel, TripSageDomainModel

    # Import domain models
    from tripsage_core.models.domain import AccommodationListing, FlightOffer

    # Import exceptions
    from tripsage_core.exceptions import CoreTripSageError, CoreValidationError
"""

__version__ = "1.0.0"

# Import key classes for convenience
from tripsage_core import exceptions
from tripsage_core.config import CoreAppSettings, get_settings, init_settings
from tripsage_core.models.base_core_model import (
    TripSageBaseResponse,
    TripSageDBModel,
    TripSageDomainModel,
    TripSageModel,
)

__all__ = [
    # Core models
    "TripSageModel",
    "TripSageDomainModel",
    "TripSageDBModel",
    "TripSageBaseResponse",
    # Exceptions
    "exceptions",
    # Config
    "CoreAppSettings",
    "get_settings",
    "init_settings",
]
