"""Flight API schemas using Pydantic V2.

This module re-exports consolidated flight schemas from schemas_common
to maintain API compatibility while eliminating duplication.

All flight-related schemas have been consolidated to
tripsage_core.models.schemas_common.flight_schemas as the single source of truth
following Pydantic V2 best practices.
"""

# Re-export all flight schemas from the consolidated location
# Re-export Airport and FlightOffer from domain model (canonical location)
from tripsage_core.models.domain.flight import Airport, FlightOffer

# Re-export CabinClass from enums (canonical location)
from tripsage_core.models.schemas_common.enums import CabinClass
from tripsage_core.models.schemas_common.flight_schemas import (
    AirportSearchRequest,
    AirportSearchResponse,
    FlightPassenger,
    FlightSearchRequest,
    FlightSearchResponse,
    MultiCityFlightSearchRequest,
    MultiCityFlightSegment,
    SavedFlightRequest,
    SavedFlightResponse,
    UpcomingFlightResponse,
)


__all__ = [
    # Request schemas
    "FlightSearchRequest",
    "MultiCityFlightSearchRequest",
    "MultiCityFlightSegment",
    "AirportSearchRequest",
    "SavedFlightRequest",
    "FlightPassenger",
    # Response schemas
    "FlightSearchResponse",
    "AirportSearchResponse",
    "SavedFlightResponse",
    "UpcomingFlightResponse",
    "FlightOffer",
    "Airport",
    # Enums
    "CabinClass",
]
