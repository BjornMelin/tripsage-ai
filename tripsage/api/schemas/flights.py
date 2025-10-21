"""Flight API schema façade that re-exports the service models."""

from tripsage_core.models.domain.flights_canonical import (
    FlightBooking,
    FlightBookingRequest,
    FlightOffer,
    FlightSearchResponse,
)
from tripsage_core.models.schemas_common.enums import BookingStatus, CabinClass
from tripsage_core.models.schemas_common.flight_schemas import FlightSearchRequest


__all__ = [
    "BookingStatus",
    "CabinClass",
    "FlightBooking",
    "FlightBookingRequest",
    "FlightOffer",
    "FlightSearchRequest",
    "FlightSearchResponse",
]
