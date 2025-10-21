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

# Re-export enums from canonical location
from tripsage_core.models.schemas_common.enums import BookingStatus, CabinClass
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
from tripsage_core.services.business.flight_service import (
    FlightBooking,
    FlightBookingRequest,
)


__all__ = [
    "Airport",
    "AirportSearchRequest",
    "AirportSearchResponse",
    # Enums
    "BookingStatus",
    "CabinClass",
    # Domain models
    "FlightBooking",
    "FlightBookingRequest",
    "FlightOffer",
    "FlightPassenger",
    # Request schemas
    "FlightSearchRequest",
    # Response schemas
    "FlightSearchResponse",
    "MultiCityFlightSearchRequest",
    "MultiCityFlightSegment",
    "SavedFlightRequest",
    "SavedFlightResponse",
    "UpcomingFlightResponse",
]
