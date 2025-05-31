"""Pydantic V2 models for the TripSage API.

This package contains organized Pydantic models with clear separation of concerns:

- common/     : Shared domain models and data structures
- requests/   : API request schemas and validation models  
- responses/  : API response schemas and output models

Import directly from the appropriate subdirectory:

    from tripsage.api.models.requests.auth import LoginRequest
    from tripsage.api.models.responses.auth import UserResponse
    from tripsage.api.models.common.trips import Trip

For shared types from tripsage_core:
    from tripsage_core.models.schemas_common import BookingStatus
"""

# Re-export shared types for convenience
from tripsage_core.models.schemas_common import (
    BookingStatus as BookingStatus,
    CancellationPolicy,
)

# Legacy aliases for backwards compatibility
PropertyType = CancellationPolicy