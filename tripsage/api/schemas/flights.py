"""Flight API schema façade that re-exports the service models."""

from tripsage_core.models.schemas_common.enums import BookingStatus, CabinClass
from tripsage_core.services.business.flight_service import (
    FlightBooking,
    FlightBookingRequest,
    FlightOffer,
    FlightSearchRequest,
    FlightSearchResponse,
)


__all__ = [
    "BookingStatus",
    "CabinClass",
    "FlightBooking",
    "FlightBookingRequest",
    "FlightOffer",
    "FlightSearchRequest",
    "FlightSearchResponse",
]
