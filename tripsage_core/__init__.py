"""TripSage Core Package.

This package contains the centralized core functionality for the TripSage application,
including models, exceptions, and shared utilities.

Modules:
- models: Core data models and schemas
- exceptions: Centralized exception handling system
- config: Core configuration settings
- utilities: Shared utility functions and helpers
"""

__version__ = "1.0.0"

# Import key classes for convenience
from tripsage_core import exceptions
from tripsage_core.config import Settings, get_settings
from tripsage_core.models.base_core_model import (
    TripSageBaseResponse,
    TripSageDBModel,
    TripSageDomainModel,
    TripSageModel,
)


__all__ = [
    # Config
    "Settings",
    "TripSageBaseResponse",
    "TripSageDBModel",
    "TripSageDomainModel",
    # Core models
    "TripSageModel",
    # Exceptions
    "exceptions",
    "get_settings",
]
